"""Ingestion Celery tasks."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.core.celery_app import CeleryConfigurationError, get_celery_app
from app.core.embedding_client import EmbeddingClientAPIError
from app.core.qdrant_client import QdrantAPIError, QdrantConnectionError
from app.ingestion.exceptions import IngestionValidationError, SourceLoadError
from app.ingestion.indexers.metadata_indexer import MetadataIndexer
from app.ingestion.indexers.vector_indexer import VectorIndexer
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.processors.chunker import SemanticChunkerProcessor
from app.ingestion.processors.cleaner import CleanerProcessor
from app.ingestion.processors.embedder import EmbeddingProcessor
from app.ingestion.processors.language_detector import LanguageDetectorProcessor
from app.ingestion.processors.metadata_extractor import MetadataExtractorProcessor
from app.ingestion.schemas import DocumentChunk, EmbeddedChunk, IngestionChunk, RawDocument, SourceConfig
from app.ingestion.sources.discord_scraper import DiscordScraperSource
from app.ingestion.sources.file_loader import FileLoaderSource
from app.ingestion.sources.web_scraper import WebScraperSource

logger = logging.getLogger(__name__)

TRANSIENT_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    SourceLoadError,
    EmbeddingClientAPIError,
    QdrantConnectionError,
    QdrantAPIError,
)


class _DummyTaskApp:
    """Fallback task app when Celery is not configured."""

    @staticmethod
    def task(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator


def _resolve_task_app():
    try:
        return get_celery_app()
    except CeleryConfigurationError as exc:
        logger.warning("celery_not_configured_for_tasks", extra={"error": str(exc)})
        return _DummyTaskApp()


task_app = _resolve_task_app()


def _serialize_documents(documents: list[RawDocument]) -> list[dict[str, Any]]:
    return [document.model_dump(mode="json") for document in documents]


def _serialize_chunks(chunks: list[DocumentChunk]) -> list[dict[str, Any]]:
    return [chunk.model_dump(mode="json") for chunk in chunks]


def _serialize_embedded_chunks(chunks: list[EmbeddedChunk]) -> list[dict[str, Any]]:
    return [chunk.model_dump(mode="json") for chunk in chunks]


@task_app.task(
    bind=True,
    autoretry_for=TRANSIENT_EXCEPTIONS,
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=4,
    name="tasks.scrape_source_task",
)
def scrape_source_task(self, source_type: str, config_data: dict[str, Any]) -> dict[str, Any]:
    """Load source documents using configured source loader."""
    task_id = getattr(getattr(self, "request", None), "id", None)
    logger.info("scrape_source_task_started", extra={"task_id": task_id, "source_type": source_type})

    config = SourceConfig.model_validate({**config_data, "source_type": source_type})
    if source_type == "web":
        documents = IngestionPipeline()._run_async(WebScraperSource().load(config))
    elif source_type == "discord":
        documents = IngestionPipeline()._run_async(DiscordScraperSource().load(config))
    elif source_type == "file":
        documents = IngestionPipeline()._run_async(FileLoaderSource().load(config))
    else:
        raise IngestionValidationError(f"unsupported source type: {source_type}")

    payload = {
        "status": "completed",
        "source_type": source_type,
        "count": len(documents),
        "documents": _serialize_documents(documents),
    }
    logger.info("scrape_source_task_completed", extra={"task_id": task_id, "count": len(documents)})
    return payload


@task_app.task(
    bind=True,
    autoretry_for=TRANSIENT_EXCEPTIONS,
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=4,
    name="tasks.process_document_task",
)
def process_document_task(self, raw_document_data: dict[str, Any]) -> dict[str, Any]:
    """Process one raw document through clean/language/metadata/chunk stages."""
    task_id = getattr(getattr(self, "request", None), "id", None)
    logger.info("process_document_task_started", extra={"task_id": task_id})

    raw_document = RawDocument.model_validate(raw_document_data)
    cleaner = CleanerProcessor()
    language_detector = LanguageDetectorProcessor()
    metadata_extractor = MetadataExtractorProcessor()
    chunker = SemanticChunkerProcessor()
    indexer = MetadataIndexer()

    cleaned = cleaner.clean_document(raw_document)
    detected_language = language_detector.detect_language(cleaned.cleaned_text)
    cleaned = cleaned.model_copy(update={"language": detected_language})
    metadata = metadata_extractor.extract(cleaned)

    persisted_doc = indexer.store_document(
        source_type=raw_document.source_type,
        source_uri=raw_document.source_uri,
        title=raw_document.title,
        raw_content=raw_document.raw_content,
        cleaned_text=cleaned.cleaned_text,
        language=cleaned.language,
        summary=cleaned.summary,
        content_hash=cleaned.content_hash,
        metadata_json={**dict(raw_document.metadata_json or {}), **metadata},
    )
    indexer.store_metadata(persisted_doc.id, metadata)

    chunk_metadata = {
        **dict(raw_document.metadata_json or {}),
        **metadata,
        "source_type": raw_document.source_type,
        "source_uri": raw_document.source_uri,
        "title": raw_document.title,
        "document_id": str(persisted_doc.id),
    }
    chunks = chunker.chunk_document(cleaned, metadata=chunk_metadata)
    db_chunks = [
        IngestionChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            content=chunk.text,
            sequence=chunk.chunk_index,
            metadata={**dict(chunk.metadata_json or {}), "token_count": chunk.token_count},
        )
        for chunk in chunks
    ]
    indexer.store_chunks(persisted_doc.id, db_chunks)

    payload = {
        "status": "completed",
        "document_id": str(persisted_doc.id),
        "chunk_count": len(chunks),
        "metadata": metadata,
        "chunks": _serialize_chunks(chunks),
    }
    logger.info(
        "process_document_task_completed",
        extra={"task_id": task_id, "document_id": str(persisted_doc.id), "chunk_count": len(chunks)},
    )
    return payload


@task_app.task(
    bind=True,
    autoretry_for=(EmbeddingClientAPIError, TimeoutError, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=4,
    name="tasks.embed_chunks_task",
)
def embed_chunks_task(self, chunks_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate embeddings for chunks."""
    task_id = getattr(getattr(self, "request", None), "id", None)
    logger.info("embed_chunks_task_started", extra={"task_id": task_id, "chunk_count": len(chunks_data)})

    chunks = [DocumentChunk.model_validate(item) for item in chunks_data]
    embedded = EmbeddingProcessor().embed_chunks(chunks)
    payload = {"status": "completed", "embedded_count": len(embedded), "embedded_chunks": _serialize_embedded_chunks(embedded)}
    logger.info("embed_chunks_task_completed", extra={"task_id": task_id, "embedded_count": len(embedded)})
    return payload


@task_app.task(
    bind=True,
    autoretry_for=(QdrantConnectionError, QdrantAPIError, TimeoutError, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=4,
    name="tasks.index_chunks_task",
)
def index_chunks_task(self, embedded_chunks_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Index embedded chunks into vector store."""
    task_id = getattr(getattr(self, "request", None), "id", None)
    logger.info("index_chunks_task_started", extra={"task_id": task_id, "chunk_count": len(embedded_chunks_data)})

    embedded_chunks = [EmbeddedChunk.model_validate(item) for item in embedded_chunks_data]
    vector_indexer = VectorIndexer()
    vector_indexer.index_chunks(embedded_chunks)
    payload = {
        "status": "completed",
        "indexed_count": len(embedded_chunks),
        "chunk_ids": [str(chunk.chunk_id) for chunk in embedded_chunks],
    }
    logger.info("index_chunks_task_completed", extra={"task_id": task_id, "indexed_count": len(embedded_chunks)})
    return payload


@task_app.task(
    bind=True,
    autoretry_for=TRANSIENT_EXCEPTIONS,
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=3,
    name="tasks.full_ingestion_pipeline_task",
)
def full_ingestion_pipeline_task(self, source_type: str, config_data: dict[str, Any]) -> dict[str, Any]:
    """Run full ingestion pipeline for one source configuration."""
    task_id = getattr(getattr(self, "request", None), "id", None)
    logger.info("full_ingestion_pipeline_task_started", extra={"task_id": task_id, "source_type": source_type})

    config = SourceConfig.model_validate({**config_data, "source_type": source_type})
    pipeline = IngestionPipeline()
    if source_type == "web":
        result = pipeline.ingest_url(config)
    elif source_type == "discord":
        result = pipeline.ingest_discord(config)
    elif source_type == "file":
        result = pipeline.ingest_file(config)
    else:
        raise IngestionValidationError(f"unsupported source type: {source_type}")
    payload = result.model_dump(mode="json")
    logger.info("full_ingestion_pipeline_task_completed", extra={"task_id": task_id, "status": payload.get("status")})
    return payload


async def run_ingestion_job(job_id: UUID) -> None:
    """Backward-compatible placeholder for older imports."""
    _ = job_id
