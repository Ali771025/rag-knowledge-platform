"""Full ingestion pipeline orchestration."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.core.embedding_client import EmbeddingClientConfigurationError
from app.core.kafka_client import KafkaClientAdapter, KafkaError
from app.ingestion.exceptions import IngestionError
from app.ingestion.indexers.metadata_indexer import MetadataIndexer
from app.ingestion.indexers.vector_indexer import VectorIndexer
from app.ingestion.processors.chunker import SemanticChunkerProcessor
from app.ingestion.processors.cleaner import CleanerProcessor
from app.ingestion.processors.deduplicator import DeduplicatorProcessor
from app.ingestion.processors.embedder import EmbeddingProcessor
from app.ingestion.processors.language_detector import LanguageDetectorProcessor
from app.ingestion.processors.metadata_extractor import MetadataExtractorProcessor
from app.ingestion.schemas import (
    CleanedDocument,
    IngestionChunk,
    IngestionPipelineResult,
    IngestionRequest,
    IngestionResult,
    RawDocument,
    SourceConfig,
)
from app.ingestion.sources.discord_scraper import DiscordScraperSource
from app.ingestion.sources.file_loader import FileLoaderSource
from app.ingestion.sources.web_scraper import WebScraperSource
from app.knowledge_graph.pipeline import KnowledgeGraphPipeline

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Coordinates source loading, processing, persistence, and graph indexing."""

    def __init__(
        self,
        web_loader: WebScraperSource | None = None,
        discord_loader: DiscordScraperSource | None = None,
        file_loader: FileLoaderSource | None = None,
        deduplicator: DeduplicatorProcessor | None = None,
        cleaner: CleanerProcessor | None = None,
        language_detector: LanguageDetectorProcessor | None = None,
        metadata_extractor: MetadataExtractorProcessor | None = None,
        metadata_indexer: MetadataIndexer | None = None,
        chunker: SemanticChunkerProcessor | None = None,
        embedding_processor: EmbeddingProcessor | None = None,
        vector_indexer: VectorIndexer | None = None,
        knowledge_graph_pipeline: KnowledgeGraphPipeline | None = None,
        kafka_client: KafkaClientAdapter | None = None,
    ) -> None:
        self.web_loader = web_loader or WebScraperSource()
        self.discord_loader = discord_loader or DiscordScraperSource()
        self.file_loader = file_loader or FileLoaderSource()
        self.deduplicator = deduplicator or DeduplicatorProcessor()
        self.cleaner = cleaner or CleanerProcessor()
        self.language_detector = language_detector or LanguageDetectorProcessor()
        self.metadata_extractor = metadata_extractor or MetadataExtractorProcessor()
        self.metadata_indexer = metadata_indexer or MetadataIndexer()
        self.chunker = chunker or SemanticChunkerProcessor()
        self.embedding_processor = embedding_processor or EmbeddingProcessor()
        self.vector_indexer = vector_indexer or VectorIndexer()
        self.knowledge_graph_pipeline = knowledge_graph_pipeline or KnowledgeGraphPipeline()
        self.kafka_client = kafka_client or KafkaClientAdapter()

    def ingest_url(self, config: SourceConfig) -> IngestionPipelineResult:
        """Load and ingest documents from web source."""
        logger.info("ingest_url_started", extra={"source_uri": config.source_uri})
        correlation_id = str(uuid4())
        documents = self._run_async(self.web_loader.load(config))
        return self.ingest_documents(
            documents,
            correlation_id=correlation_id,
            source_type_override=config.source_type,
            source_uri_override=config.source_uri,
        )

    def ingest_discord(self, config: SourceConfig) -> IngestionPipelineResult:
        """Load and ingest documents from Discord source."""
        logger.info("ingest_discord_started", extra={"source_uri": config.source_uri})
        correlation_id = str(uuid4())
        documents = self._run_async(self.discord_loader.load(config))
        return self.ingest_documents(
            documents,
            correlation_id=correlation_id,
            source_type_override=config.source_type,
            source_uri_override=config.source_uri,
        )

    def ingest_file(self, config: SourceConfig) -> IngestionPipelineResult:
        """Load and ingest documents from file source."""
        logger.info("ingest_file_started", extra={"source_uri": config.source_uri})
        correlation_id = str(uuid4())
        documents = self._run_async(self.file_loader.load(config))
        return self.ingest_documents(
            documents,
            correlation_id=correlation_id,
            source_type_override=config.source_type,
            source_uri_override=config.source_uri,
        )

    def ingest_documents(
        self,
        documents: list[RawDocument],
        *,
        correlation_id: str | None = None,
        source_type_override: str | None = None,
        source_uri_override: str | None = None,
    ) -> IngestionPipelineResult:
        """Ingest already-loaded raw documents through all processing stages."""
        now = datetime.now(timezone.utc)
        resolved_correlation_id = correlation_id or str(uuid4())
        source_type = source_type_override or (documents[0].source_type if documents else "docs")
        source_uri = source_uri_override or (documents[0].source_uri if documents else "unknown")

        job = self.metadata_indexer.create_ingestion_job(
            source_type=source_type,
            source_uri=source_uri,
            status="pending",
            stats_json={"received_documents": len(documents)},
        )
        errors: list[str] = []
        warnings: list[str] = []
        processed_docs = 0
        total_chunks = 0
        embedded_chunks = 0
        last_document_id: UUID | None = None

        try:
            self.metadata_indexer.update_ingestion_job(job.id, status="running")
            logger.info("ingestion_job_running", extra={"job_id": str(job.id), "documents_received": len(documents)})
            ingestion_job_id = str(job.id)
            self._publish_event(
                "ingestion.source.submitted",
                {
                    "source_type": source_type,
                    "source_uri": source_uri,
                    "documents_received": len(documents),
                    "status": "running",
                },
                correlation_id=resolved_correlation_id,
                ingestion_job_id=ingestion_job_id,
            )

            for raw_document in documents:
                self._publish_event(
                    "ingestion.document.scraped",
                    {
                        "document_id": str(raw_document.document_id),
                        "source_type": raw_document.source_type,
                        "source_uri": raw_document.source_uri,
                        "title": raw_document.title,
                    },
                    correlation_id=resolved_correlation_id,
                    ingestion_job_id=ingestion_job_id,
                )

            deduped_documents = self.deduplicator.filter_duplicates(documents)
            logger.info(
                "ingestion_stage_deduplicate_completed",
                extra={"job_id": str(job.id), "before": len(documents), "after": len(deduped_documents)},
            )

            for raw_document in deduped_documents:
                try:
                    cleaned = self.cleaner.clean_document(raw_document)
                    detected_language = self.language_detector.detect_language(cleaned.cleaned_text)
                    cleaned = cleaned.model_copy(update={"language": detected_language})
                    self._publish_event(
                        "ingestion.document.cleaned",
                        {
                            "document_id": str(raw_document.document_id),
                            "source_uri": raw_document.source_uri,
                            "language": cleaned.language,
                            "content_hash": cleaned.content_hash,
                        },
                        correlation_id=resolved_correlation_id,
                        ingestion_job_id=ingestion_job_id,
                    )
                    extracted_metadata = self.metadata_extractor.extract(cleaned)

                    persisted_doc = self.metadata_indexer.store_document(
                        source_type=raw_document.source_type,
                        source_uri=raw_document.source_uri,
                        title=raw_document.title,
                        raw_content=raw_document.raw_content,
                        cleaned_text=cleaned.cleaned_text,
                        language=cleaned.language,
                        summary=cleaned.summary,
                        content_hash=cleaned.content_hash,
                        metadata_json={**dict(raw_document.metadata_json or {}), **extracted_metadata},
                    )
                    last_document_id = persisted_doc.id

                    self.metadata_indexer.store_metadata(persisted_doc.id, extracted_metadata)

                    chunk_metadata = {
                        **dict(raw_document.metadata_json or {}),
                        **extracted_metadata,
                        "source_type": raw_document.source_type,
                        "source_uri": raw_document.source_uri,
                        "title": raw_document.title,
                        "document_id": str(persisted_doc.id),
                    }
                    chunks = self.chunker.chunk_document(cleaned, metadata=chunk_metadata)
                    total_chunks += len(chunks)
                    self._publish_event(
                        "ingestion.chunks.created",
                        {
                            "document_id": str(persisted_doc.id),
                            "source_uri": raw_document.source_uri,
                            "chunk_count": len(chunks),
                        },
                        correlation_id=resolved_correlation_id,
                        ingestion_job_id=ingestion_job_id,
                    )

                    db_chunks_payload = [
                        IngestionChunk(
                            chunk_id=chunk.chunk_id,
                            document_id=chunk.document_id,
                            content=chunk.text,
                            sequence=chunk.chunk_index,
                            metadata={
                                **dict(chunk.metadata_json or {}),
                                "token_count": chunk.token_count,
                                "content_hash": chunk.content_hash,
                            },
                        )
                        for chunk in chunks
                    ]
                    self.metadata_indexer.store_chunks(persisted_doc.id, db_chunks_payload)

                    embedded = []
                    try:
                        embedded = self.embedding_processor.embed_chunks(chunks)
                        embedded_chunks += len(embedded)
                        self._publish_event(
                            "ingestion.embeddings.generated",
                            {
                                "document_id": str(persisted_doc.id),
                                "chunk_count": len(embedded),
                                "embedding_model": "text-embedding-3-large",
                            },
                            correlation_id=resolved_correlation_id,
                            ingestion_job_id=ingestion_job_id,
                        )
                    except Exception as exc:
                        if self._is_embedding_configuration_error(exc):
                            logger.warning(
                                "ingestion_embedding_skipped_missing_configuration",
                                extra={
                                    "job_id": str(job.id),
                                    "document_id": str(persisted_doc.id),
                                    "error": str(exc),
                                },
                            )
                            warnings.append("embedding_skipped_missing_configuration")
                        else:
                            logger.warning(
                                "ingestion_embedding_partial_failure",
                                extra={
                                    "job_id": str(job.id),
                                    "document_id": str(persisted_doc.id),
                                    "error": str(exc),
                                },
                            )
                            errors.append(f"embedding:{persisted_doc.id}:{exc}")

                    if embedded:
                        try:
                            self.vector_indexer.index_chunks(embedded)
                            self._publish_event(
                                "ingestion.vectors.indexed",
                                {
                                    "document_id": str(persisted_doc.id),
                                    "indexed_count": len(embedded),
                                },
                                correlation_id=resolved_correlation_id,
                                ingestion_job_id=ingestion_job_id,
                            )
                        except Exception as exc:
                            logger.warning(
                                "ingestion_vector_index_partial_failure",
                                extra={"job_id": str(job.id), "document_id": str(persisted_doc.id), "error": str(exc)},
                            )
                            errors.append(f"vector_index:{persisted_doc.id}:{exc}")

                    try:
                        kg_result = self.knowledge_graph_pipeline.build_for_document(
                            str(persisted_doc.id),
                            chunks,
                            correlation_id=resolved_correlation_id,
                            ingestion_job_id=ingestion_job_id,
                        )
                        if kg_result.get("status") in {"partial", "failed"}:
                            errors.extend([f"kg:{error}" for error in kg_result.get("errors", [])])
                    except Exception as exc:
                        if self._is_strict_kafka_graph_error(exc):
                            raise
                        logger.warning(
                            "ingestion_kg_partial_failure",
                            extra={"job_id": str(job.id), "document_id": str(persisted_doc.id), "error": str(exc)},
                        )
                        errors.append(f"kg_pipeline:{persisted_doc.id}:{exc}")

                    processed_docs += 1
                except IngestionError:
                    raise
                except Exception as exc:
                    logger.warning(
                        "ingestion_document_failed",
                        extra={"job_id": str(job.id), "source_uri": raw_document.source_uri, "error": str(exc)},
                    )
                    errors.append(f"document:{raw_document.source_uri}:{exc}")
                    continue

            status = self._derive_status(
                processed_docs=processed_docs,
                total_chunks=total_chunks,
                errors=errors,
            )
            if processed_docs <= 0 and not errors:
                errors.append("no_documents_processed")
            if processed_docs > 0 and total_chunks <= 0 and not errors:
                errors.append("no_chunks_generated")
            self.metadata_indexer.update_ingestion_job(
                job.id,
                status=status,
                error_message="\n".join(errors[:20]) if errors else None,
                stats_json={
                    "received_documents": len(documents),
                    "deduplicated_documents": len(deduped_documents),
                    "processed_documents": processed_docs,
                    "total_chunks": total_chunks,
                    "embedded_chunks": embedded_chunks,
                    "warnings": len(warnings),
                    "errors": len(errors),
                },
                completed_at=datetime.now(timezone.utc),
            )
            self._publish_event(
                "ingestion.completed",
                {
                    "status": status,
                    "source_type": source_type,
                    "source_uri": source_uri,
                    "processed_documents": processed_docs,
                    "total_chunks": total_chunks,
                    "embedded_chunks": embedded_chunks,
                    "errors": len(errors),
                    "warnings": len(warnings),
                },
                correlation_id=resolved_correlation_id,
                ingestion_job_id=ingestion_job_id,
            )
            return IngestionPipelineResult(
                job_id=job.id,
                status=status,  # type: ignore[arg-type]
                document_id=last_document_id,
                chunks_total=total_chunks,
                chunks_embedded=embedded_chunks,
                errors=errors,
                warnings=warnings,
                created_at=now,
                updated_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            logger.exception("ingestion_pipeline_failed", exc_info=exc)
            self.metadata_indexer.update_ingestion_job(
                job.id,
                status="failed",
                error_message=str(exc),
                stats_json={"errors": len(errors) + 1},
                completed_at=datetime.now(timezone.utc),
            )
            try:
                self._publish_event(
                    "ingestion.failed",
                    {
                        "status": "failed",
                        "source_type": source_type,
                        "source_uri": source_uri,
                        "processed_documents": processed_docs,
                        "total_chunks": total_chunks,
                        "embedded_chunks": embedded_chunks,
                        "error": str(exc),
                        "errors": len(errors) + 1,
                    },
                    correlation_id=resolved_correlation_id,
                    ingestion_job_id=str(job.id),
                )
            except Exception:
                if self.kafka_client.strict_mode:
                    raise
            return IngestionPipelineResult(
                job_id=job.id,
                status="failed",
                document_id=last_document_id,
                chunks_total=total_chunks,
                chunks_embedded=embedded_chunks,
                errors=[*errors, str(exc)],
                warnings=warnings,
                created_at=now,
                updated_at=datetime.now(timezone.utc),
            )

    async def run(self, request: IngestionRequest) -> IngestionResult:
        """Backward-compatible async wrapper for older pipeline interface."""
        config = SourceConfig(
            source_type=request.source_type,
            source_uri=request.source_uri,
            max_items=1000,
            timeout_seconds=30,
            options=request.metadata,
        )
        if request.source_type == "web":
            result = self.ingest_url(config)
        elif request.source_type == "discord":
            result = self.ingest_discord(config)
        elif request.source_type == "file":
            result = self.ingest_file(config)
        else:
            documents: list[RawDocument] = []
            result = self.ingest_documents(documents)
        return IngestionResult(
            job_id=result.job_id,
            status=result.status,  # type: ignore[arg-type]
            processed_chunks=result.chunks_total,
            errors=result.errors,
            updated_at=result.updated_at,
        )

    def _run_async(self, coroutine):
        """Run async loader coroutine from sync context."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coroutine)
            return future.result()

    def _derive_status(self, *, processed_docs: int, total_chunks: int, errors: list[str]) -> str:
        # A successful ingestion must produce at least one processed document and one chunk.
        if processed_docs <= 0 or total_chunks <= 0:
            return "failed"
        if not errors:
            return "completed"
        if processed_docs > 0:
            return "partial"
        return "failed"

    def _publish_event(
        self,
        event_name: str,
        payload: dict[str, Any],
        *,
        correlation_id: str,
        ingestion_job_id: str,
    ) -> None:
        try:
            self.kafka_client.publish_event(
                event_name=event_name,
                payload=payload,
                correlation_id=correlation_id,
                ingestion_job_id=ingestion_job_id,
            )
        except KafkaError as exc:
            logger.warning(
                "kafka_event_publish_failed",
                extra={
                    "event_name": event_name,
                    "correlation_id": correlation_id,
                    "ingestion_job_id": ingestion_job_id,
                    "error": str(exc),
                },
            )
            if self.kafka_client.strict_mode:
                raise IngestionError(f"kafka_event_publish_failed:{event_name}") from exc

    def _is_strict_kafka_graph_error(self, error: Exception) -> bool:
        if not self.kafka_client.strict_mode:
            return False
        return "kafka_event_publish_failed" in str(error)

    def _is_embedding_configuration_error(self, error: Exception) -> bool:
        for exc in self._iter_error_chain(error):
            if isinstance(exc, EmbeddingClientConfigurationError):
                return True
            if "openai_api_key" in str(exc).strip().lower():
                return True
        return False

    def _iter_error_chain(self, error: Exception):
        seen: set[int] = set()
        current: BaseException | None = error
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if isinstance(current, Exception):
                yield current
            if current.__cause__ is not None:
                current = current.__cause__
                continue
            current = current.__context__
