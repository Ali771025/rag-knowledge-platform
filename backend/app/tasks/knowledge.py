"""Knowledge-domain Celery task orchestration.

This module keeps task bodies thin and delegates business logic to existing
ingestion/graph components where possible.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy import desc, or_, select

from app.core.celery_app import CeleryConfigurationError, get_celery_app
from app.core.database import SessionLocal
from app.core.task_base import BaseTaskWithRetry
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.document_job import DocumentProcessingJob
from app.services.tasks.task_logging import TaskLogger
from app.services.tasks.task_metrics import TaskMetrics

logger = logging.getLogger(__name__)
task_logger = TaskLogger()
task_metrics = TaskMetrics()

_MAX_DOCUMENT_CONTENT_CHARS = 2_000_000
_MAX_BATCH_SIZE = 500
_SUPPORTED_GRAPH_SCOPES = {"full", "incremental", "recent"}
_SOURCE_TYPES = {"web", "discord", "file", "docs"}
_JOB_STATUSES = {"pending", "running", "completed", "failed"}
_COMPACT_ERROR_MAX = 800


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
        logger.warning("celery_not_configured_for_knowledge_tasks", extra={"error": str(exc)})
        return _DummyTaskApp()


task_app = _resolve_task_app()


def _request_context(task: Any) -> dict[str, Any]:
    request = getattr(task, "request", None)
    delivery_info = getattr(request, "delivery_info", {}) or {}
    return {
        "task_id": str(getattr(request, "id", "") or ""),
        "task_name": str(getattr(task, "name", "") or ""),
        "queue": delivery_info.get("routing_key") if isinstance(delivery_info, dict) else None,
        "retry_count": int(getattr(request, "retries", 0) or 0),
    }


def _log_task_failure(context: dict[str, Any], started: float, exc: Exception) -> None:
    duration_seconds = perf_counter() - started
    task_logger.log_task_failure(
        task_id=context["task_id"],
        task_name=context["task_name"],
        queue=context["queue"],
        duration_ms=int(duration_seconds * 1000),
        retry_count=context["retry_count"],
        error=str(exc)[:_COMPACT_ERROR_MAX],
    )
    task_metrics.record_task_failure(context["task_name"], queue=context["queue"])
    task_metrics.record_task_retry(context["task_name"], retry_count=context["retry_count"], queue=context["queue"])


def _update_progress(task: Any, *, current: int, total: int, step: str, **extra: Any) -> None:
    meta = {
        "progress": {
            "current": current,
            "total": total,
            "percent": round((current / total) * 100.0, 2) if total > 0 else None,
            "step": step,
        },
        **extra,
    }
    try:
        task.update_state(state="STARTED", meta=meta)
    except Exception:
        logger.debug("knowledge_task_progress_update_failed", exc_info=True)


def _validate_document_payload(
    document_id: str,
    document_content: str,
    document_metadata: dict[str, Any],
) -> tuple[UUID, str, dict[str, Any]]:
    try:
        resolved_document_id = UUID(str(document_id).strip())
    except Exception as exc:
        raise ValueError("document_id must be a valid UUID string") from exc

    if not isinstance(document_content, str) or not document_content.strip():
        raise ValueError("document_content must be a non-empty string")
    if len(document_content) > _MAX_DOCUMENT_CONTENT_CHARS:
        raise ValueError("document_content exceeds configured size limit")

    if not isinstance(document_metadata, dict):
        raise ValueError("document_metadata must be a dictionary")
    return resolved_document_id, document_content, dict(document_metadata)


def _validate_document_ids(document_ids: list[str]) -> list[UUID]:
    if not isinstance(document_ids, list) or not document_ids:
        raise ValueError("document_ids must be a non-empty list")
    if len(document_ids) > _MAX_BATCH_SIZE:
        raise ValueError(f"document_ids exceeds max batch size of {_MAX_BATCH_SIZE}")

    seen: set[UUID] = set()
    unique_ids: list[UUID] = []
    for raw_id in document_ids:
        try:
            resolved_id = UUID(str(raw_id).strip())
        except Exception as exc:
            raise ValueError(f"invalid UUID in document_ids: {raw_id}") from exc
        if resolved_id in seen:
            continue
        seen.add(resolved_id)
        unique_ids.append(resolved_id)
    return unique_ids


def _validate_scope(scope: str) -> str:
    resolved_scope = str(scope or "").strip().lower()
    if resolved_scope not in _SUPPORTED_GRAPH_SCOPES:
        allowed = ", ".join(sorted(_SUPPORTED_GRAPH_SCOPES))
        raise ValueError(f"scope must be one of: {allowed}")
    return resolved_scope


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _idempotency_key(document_id: UUID, content_hash: str) -> str:
    return f"{document_id}:{content_hash}"


def _normalize_source_type(metadata: dict[str, Any]) -> str:
    source_type = str(metadata.get("source_type", "docs")).strip().lower()
    return source_type if source_type in _SOURCE_TYPES else "docs"


def _resolve_source_uri(document_id: UUID, metadata: dict[str, Any]) -> str:
    candidate = str(metadata.get("source_uri", "") or "").strip()
    if candidate:
        return candidate
    return f"task://knowledge/{document_id}"


def _safe_transition(current: str, target: str) -> str:
    if target not in _JOB_STATUSES:
        return current
    if current == target:
        return current
    if current == "completed" and target != "completed":
        return current
    if current == "failed" and target == "pending":
        return current
    return target


def _get_or_create_document_job(document_id: UUID) -> DocumentProcessingJob:
    with SessionLocal() as session:
        stmt = (
            select(DocumentProcessingJob)
            .where(DocumentProcessingJob.document_id == document_id)
            .order_by(desc(DocumentProcessingJob.created_at))
            .limit(1)
        )
        existing = session.scalar(stmt)
        if existing is not None:
            return existing
        created = DocumentProcessingJob(
            document_id=document_id,
            processing_status="pending",
            embedding_status="pending",
            graph_status="pending",
        )
        session.add(created)
        session.commit()
        session.refresh(created)
        return created


def _has_active_job(document_id: UUID) -> bool:
    with SessionLocal() as session:
        stmt = select(DocumentProcessingJob.id).where(
            DocumentProcessingJob.document_id == document_id,
            or_(
                DocumentProcessingJob.processing_status == "running",
                DocumentProcessingJob.embedding_status == "running",
                DocumentProcessingJob.graph_status == "running",
            ),
        )
        return session.scalar(stmt) is not None


def _set_document_job_status(
    document_id: UUID,
    *,
    processing_status: str | None = None,
    embedding_status: str | None = None,
    graph_status: str | None = None,
    error_message: str | None = None,
) -> None:
    with SessionLocal() as session:
        stmt = (
            select(DocumentProcessingJob)
            .where(DocumentProcessingJob.document_id == document_id)
            .order_by(desc(DocumentProcessingJob.created_at))
            .limit(1)
        )
        job = session.scalar(stmt)
        if job is None:
            job = DocumentProcessingJob(document_id=document_id)
            session.add(job)
            session.flush()

        if processing_status is not None:
            job.processing_status = _safe_transition(str(job.processing_status), processing_status)
        if embedding_status is not None:
            job.embedding_status = _safe_transition(str(job.embedding_status), embedding_status)
        if graph_status is not None:
            job.graph_status = _safe_transition(str(job.graph_status), graph_status)

        if (
            job.processing_status == "completed"
            and job.embedding_status == "completed"
            and job.graph_status == "completed"
            and job.completed_at is None
        ):
            job.completed_at = datetime.now(timezone.utc)
        if (
            "failed" in {str(job.processing_status), str(job.embedding_status), str(job.graph_status)}
            and job.completed_at is None
        ):
            job.completed_at = datetime.now(timezone.utc)

        if error_message:
            # Thin placeholder for future richer failure bookkeeping in task_logs.
            logger.warning(
                "document_processing_job_marked_failed",
                extra={"document_id": str(document_id), "error": error_message[:_COMPACT_ERROR_MAX]},
            )

        session.add(job)
        session.commit()


def _load_document(document_id: UUID) -> Document | None:
    with SessionLocal() as session:
        return session.get(Document, document_id)


def _persist_document_content(
    *,
    requested_document_id: UUID,
    cleaned_document: Any,
    raw_content: str,
    metadata_json: dict[str, Any],
) -> Document:
    from app.ingestion.indexers.metadata_indexer import MetadataIndexer

    indexer = MetadataIndexer()
    stored = indexer.store_document(
        source_type=_normalize_source_type(metadata_json),
        source_uri=_resolve_source_uri(requested_document_id, metadata_json),
        title=str(metadata_json.get("title", "") or "") or None,
        raw_content=raw_content,
        cleaned_text=cleaned_document.cleaned_text,
        language=cleaned_document.language,
        summary=cleaned_document.summary,
        content_hash=cleaned_document.content_hash,
        metadata_json=metadata_json,
    )
    return stored


def _chunk_document(document_id: UUID, document_content: str, document_metadata: dict[str, Any]) -> tuple[Any, dict[str, Any], list[Any]]:
    from app.ingestion.processors.chunker import SemanticChunkerProcessor
    from app.ingestion.processors.cleaner import CleanerProcessor
    from app.ingestion.processors.language_detector import LanguageDetectorProcessor
    from app.ingestion.processors.metadata_extractor import MetadataExtractorProcessor
    from app.ingestion.schemas import RawDocument

    raw_document = RawDocument(
        document_id=document_id,
        source_type=_normalize_source_type(document_metadata),  # type: ignore[arg-type]
        source_uri=_resolve_source_uri(document_id, document_metadata),
        title=str(document_metadata.get("title", "") or "") or None,
        raw_content=document_content,
        metadata_json=dict(document_metadata),
    )
    cleaner = CleanerProcessor()
    language_detector = LanguageDetectorProcessor()
    metadata_extractor = MetadataExtractorProcessor()
    chunker = SemanticChunkerProcessor()

    cleaned = cleaner.clean_document(raw_document)
    detected_language = language_detector.detect_language(cleaned.cleaned_text)
    cleaned = cleaned.model_copy(update={"language": detected_language})
    extracted_metadata = metadata_extractor.extract(cleaned)
    merged_metadata = {**dict(document_metadata), **dict(extracted_metadata)}
    chunks = chunker.chunk_document(cleaned, metadata=merged_metadata)
    return cleaned, extracted_metadata, chunks


def _persist_chunks(document_id: UUID, chunks: list[Any]) -> None:
    from app.ingestion.indexers.metadata_indexer import MetadataIndexer
    from app.ingestion.schemas import IngestionChunk

    ingestion_chunks = [
        IngestionChunk(
            chunk_id=chunk.chunk_id,
            document_id=document_id,
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
    MetadataIndexer().store_chunks(document_id, ingestion_chunks)


def _generate_embeddings(chunks: list[Any]) -> list[Any]:
    from app.ingestion.processors.embedder import EmbeddingProcessor

    return EmbeddingProcessor().embed_chunks(chunks)


def _persist_embeddings(embeddings: list[Any]) -> dict[str, Any]:
    from app.ingestion.indexers.vector_indexer import VectorIndexer

    VectorIndexer().index_chunks(embeddings)
    return {"persisted": True, "embedded_count": len(embeddings)}


def _extract_entities_and_update_graph(document_id: UUID, chunks: list[Any]) -> dict[str, Any]:
    from app.knowledge_graph.pipeline import KnowledgeGraphPipeline

    result = KnowledgeGraphPipeline().build_for_document(document_id=str(document_id), chunks=chunks)
    return {
        "status": str(result.get("status", "failed")),
        "entity_count": int(result.get("entity_count", 0)),
        "relation_count": int(result.get("relation_count", 0)),
        "errors": list(result.get("errors", [])),
    }


def _estimate_tokens(chunks: list[Any]) -> int:
    token_total = 0
    for chunk in chunks:
        try:
            token_total += int(chunk.token_count or 0)
        except Exception:
            continue
    return token_total


def _track_cost_token_placeholder(document_id: UUID, token_count: int, metadata: dict[str, Any]) -> None:
    """Thin adapter placeholder for future cost tracking integration."""
    logger.debug(
        "knowledge_cost_tracking_placeholder",
        extra={
            "document_id": str(document_id),
            "token_count": token_count,
            "source_type": metadata.get("source_type"),
        },
    )


def _chunk_rows_to_models(chunk_rows: list[Chunk]) -> list[Any]:
    from app.ingestion.schemas import DocumentChunk

    models: list[DocumentChunk] = []
    for row in chunk_rows:
        content_hash = str(row.content_hash or _content_hash(row.text))
        models.append(
            DocumentChunk(
                chunk_id=row.id,
                document_id=row.document_id,
                chunk_index=row.chunk_index,
                text=row.text,
                token_count=row.token_count,
                content_hash=content_hash,
                metadata_json=dict(row.metadata_json or {}),
            )
        )
    return models


def _load_document_chunks(document_id: UUID, *, limit: int = 5000) -> list[Any]:
    from app.ingestion.indexers.metadata_indexer import MetadataIndexer

    chunk_rows = MetadataIndexer().list_chunks(document_id=document_id, limit=limit, offset=0)
    return _chunk_rows_to_models(chunk_rows)


def _resolve_graph_targets(scope: str) -> list[UUID]:
    with SessionLocal() as session:
        if scope == "incremental":
            stmt = select(DocumentProcessingJob.document_id).where(
                DocumentProcessingJob.processing_status == "completed",
                DocumentProcessingJob.graph_status != "completed",
            )
            return [row for row in session.scalars(stmt).all()]

        stmt = select(Document.id).order_by(Document.created_at.desc())
        if scope == "recent":
            stmt = stmt.limit(100)
        return [row for row in session.scalars(stmt).all()]


def _is_duplicate_request(document: Document | None, content_hash: str, job: DocumentProcessingJob | None) -> bool:
    if document is None:
        return False
    if document.content_hash != content_hash:
        return False
    if job is None:
        return False
    return (
        str(job.processing_status) == "completed"
        and str(job.embedding_status) == "completed"
        and str(job.graph_status) == "completed"
    )


@task_app.task(bind=True, base=BaseTaskWithRetry, name="app.tasks.knowledge.process_document_async")
def process_document_async(self, document_id: str, document_content: str, document_metadata: dict[str, Any]) -> dict[str, Any]:
    """Process one document through chunking, embeddings, vector index, and graph update."""
    started = perf_counter()
    context = _request_context(self)
    task_logger.log_task_started(
        task_id=context["task_id"],
        task_name=context["task_name"],
        queue=context["queue"],
        retry_count=context["retry_count"],
    )
    task_metrics.record_task_started(context["task_name"], queue=context["queue"])

    requested_document_id, content, metadata = _validate_document_payload(
        document_id=document_id,
        document_content=document_content,
        document_metadata=document_metadata,
    )
    _update_progress(self, current=1, total=7, step="validated_input", document_id=str(requested_document_id))

    if _has_active_job(requested_document_id):
        return {
            "status": "skipped",
            "reason": "active_job_exists",
            "document_id": str(requested_document_id),
        }

    existing_document = _load_document(requested_document_id)
    latest_job = _get_or_create_document_job(requested_document_id)
    content_hash = _content_hash(content)
    idempotency_key = _idempotency_key(requested_document_id, content_hash)
    if _is_duplicate_request(existing_document, content_hash, latest_job):
        duration_seconds = perf_counter() - started
        task_logger.log_task_success(
            task_id=context["task_id"],
            task_name=context["task_name"],
            queue=context["queue"],
            duration_ms=int(duration_seconds * 1000),
            retry_count=context["retry_count"],
        )
        task_metrics.record_task_success(context["task_name"], duration_seconds=duration_seconds, queue=context["queue"])
        return {
            "status": "skipped",
            "reason": "duplicate_ingestion",
            "document_id": str(requested_document_id),
            "idempotency_key": idempotency_key,
        }

    try:
        _set_document_job_status(requested_document_id, processing_status="running", embedding_status="pending", graph_status="pending")
        _update_progress(self, current=2, total=7, step="chunking")
        cleaned_document, extracted_metadata, chunks = _chunk_document(requested_document_id, content, metadata)

        _update_progress(self, current=3, total=7, step="persist_document")
        merged_metadata = {
            **dict(metadata),
            **dict(extracted_metadata),
            "idempotency_key": idempotency_key,
        }
        persisted_document = _persist_document_content(
            requested_document_id=requested_document_id,
            cleaned_document=cleaned_document,
            raw_content=content,
            metadata_json=merged_metadata,
        )
        if persisted_document.id != requested_document_id:
            # Keep the requested doc-id job from remaining in running state when
            # idempotent upsert resolves to an existing canonical document row.
            _set_document_job_status(requested_document_id, processing_status="completed")
        _persist_chunks(persisted_document.id, chunks)
        _set_document_job_status(persisted_document.id, processing_status="completed")

        _update_progress(self, current=4, total=7, step="embedding")
        _set_document_job_status(persisted_document.id, embedding_status="running")
        embeddings = _generate_embeddings(chunks)

        _update_progress(self, current=5, total=7, step="qdrant_persistence")
        vector_result = _persist_embeddings(embeddings)
        _set_document_job_status(persisted_document.id, embedding_status="completed")

        _update_progress(self, current=6, total=7, step="knowledge_graph")
        _set_document_job_status(persisted_document.id, graph_status="running")
        graph_result = _extract_entities_and_update_graph(persisted_document.id, chunks)
        if graph_result["status"] in {"completed", "partial"}:
            _set_document_job_status(persisted_document.id, graph_status="completed")
        else:
            _set_document_job_status(
                persisted_document.id,
                graph_status="failed",
                error_message="knowledge graph update failed",
            )

        _update_progress(self, current=7, total=7, step="finalize")
        token_count = _estimate_tokens(chunks)
        _track_cost_token_placeholder(persisted_document.id, token_count, merged_metadata)

        duration_seconds = perf_counter() - started
        duration_ms = int(duration_seconds * 1000)
        payload = {
            "status": "completed",
            "requested_document_id": str(requested_document_id),
            "document_id": str(persisted_document.id),
            "idempotency_key": idempotency_key,
            "chunk_count": len(chunks),
            "embedded_count": len(embeddings),
            "vector_result": vector_result,
            "graph_result": graph_result,
            "token_estimate": token_count,
        }
        task_logger.log_task_success(
            task_id=context["task_id"],
            task_name=context["task_name"],
            queue=context["queue"],
            duration_ms=duration_ms,
            retry_count=context["retry_count"],
        )
        task_metrics.record_task_success(context["task_name"], duration_seconds=duration_seconds, queue=context["queue"])
        return payload
    except Exception as exc:
        _set_document_job_status(
            requested_document_id,
            processing_status="failed",
            embedding_status="failed",
            graph_status="failed",
            error_message=str(exc),
        )
        _log_task_failure(context, started, exc)
        raise


@task_app.task(bind=True, base=BaseTaskWithRetry, name="app.tasks.knowledge.batch_embed_documents")
def batch_embed_documents(self, document_ids: list[str], force_reindex: bool = False) -> dict[str, Any]:
    """Embed and persist vectors for a batch of already-chunked documents."""
    started = perf_counter()
    context = _request_context(self)
    task_logger.log_task_started(
        task_id=context["task_id"],
        task_name=context["task_name"],
        queue=context["queue"],
        retry_count=context["retry_count"],
    )
    task_metrics.record_task_started(context["task_name"], queue=context["queue"])

    resolved_ids = _validate_document_ids(document_ids)
    processed = 0
    skipped = 0
    failed = 0
    total = len(resolved_ids)

    try:
        for index, document_uuid in enumerate(resolved_ids, start=1):
            _update_progress(self, current=index, total=max(total, 1), step="embedding_batch", document_id=str(document_uuid))
            if _has_active_job(document_uuid):
                skipped += 1
                continue

            job = _get_or_create_document_job(document_uuid)
            if str(job.embedding_status) == "completed" and not force_reindex:
                skipped += 1
                continue

            chunks = _load_document_chunks(document_uuid)
            if not chunks:
                skipped += 1
                continue

            try:
                _set_document_job_status(document_uuid, embedding_status="running")
                embeddings = _generate_embeddings(chunks)
                _persist_embeddings(embeddings)
                _set_document_job_status(document_uuid, embedding_status="completed")
                processed += 1
            except Exception as doc_exc:
                _set_document_job_status(document_uuid, embedding_status="failed", error_message=str(doc_exc))
                failed += 1

        duration_seconds = perf_counter() - started
        duration_ms = int(duration_seconds * 1000)
        payload = {
            "status": "completed",
            "total_documents": total,
            "processed_documents": processed,
            "skipped_documents": skipped,
            "failed_documents": failed,
            "force_reindex": bool(force_reindex),
        }
        task_logger.log_task_success(
            task_id=context["task_id"],
            task_name=context["task_name"],
            queue=context["queue"],
            duration_ms=duration_ms,
            retry_count=context["retry_count"],
        )
        task_metrics.record_task_success(context["task_name"], duration_seconds=duration_seconds, queue=context["queue"])
        return payload
    except Exception as exc:
        _log_task_failure(context, started, exc)
        raise


@task_app.task(bind=True, base=BaseTaskWithRetry, name="app.tasks.knowledge.rebuild_knowledge_graph")
def rebuild_knowledge_graph(self, scope: str) -> dict[str, Any]:
    """Rebuild graph links for selected document scope using existing graph pipeline."""
    started = perf_counter()
    context = _request_context(self)
    task_logger.log_task_started(
        task_id=context["task_id"],
        task_name=context["task_name"],
        queue=context["queue"],
        retry_count=context["retry_count"],
    )
    task_metrics.record_task_started(context["task_name"], queue=context["queue"])

    resolved_scope = _validate_scope(scope)
    targets = _resolve_graph_targets(resolved_scope)
    updated = 0
    skipped = 0
    failed = 0

    try:
        for index, document_uuid in enumerate(targets, start=1):
            _update_progress(
                self,
                current=index,
                total=max(len(targets), 1),
                step="graph_rebuild",
                document_id=str(document_uuid),
                scope=resolved_scope,
            )
            chunks = _load_document_chunks(document_uuid)
            if not chunks:
                skipped += 1
                continue
            try:
                _set_document_job_status(document_uuid, graph_status="running")
                graph_result = _extract_entities_and_update_graph(document_uuid, chunks)
                if graph_result["status"] in {"completed", "partial"}:
                    _set_document_job_status(document_uuid, graph_status="completed")
                    updated += 1
                else:
                    _set_document_job_status(document_uuid, graph_status="failed", error_message="graph status failed")
                    failed += 1
            except Exception as graph_exc:
                _set_document_job_status(document_uuid, graph_status="failed", error_message=str(graph_exc))
                failed += 1

        duration_seconds = perf_counter() - started
        duration_ms = int(duration_seconds * 1000)
        payload = {
            "status": "completed",
            "scope": resolved_scope,
            "targets": len(targets),
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
        }
        task_logger.log_task_success(
            task_id=context["task_id"],
            task_name=context["task_name"],
            queue=context["queue"],
            duration_ms=duration_ms,
            retry_count=context["retry_count"],
        )
        task_metrics.record_task_success(context["task_name"], duration_seconds=duration_seconds, queue=context["queue"])
        return payload
    except Exception as exc:
        _log_task_failure(context, started, exc)
        raise


__all__ = ["process_document_async", "batch_embed_documents", "rebuild_knowledge_graph"]
