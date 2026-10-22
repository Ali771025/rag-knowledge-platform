"""Knowledge graph Celery tasks."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.core.celery_app import CeleryConfigurationError, get_celery_app
from app.core.claude_client import ClaudeClientAPIError
from app.core.neo4j_client import Neo4jConnectionError, Neo4jQueryError
from app.ingestion.exceptions import IngestionValidationError
from app.ingestion.schemas import DocumentChunk
from app.knowledge_graph.pipeline import KnowledgeGraphPipeline

logger = logging.getLogger(__name__)

TRANSIENT_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    Neo4jConnectionError,
    Neo4jQueryError,
    ClaudeClientAPIError,
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
        logger.warning("celery_not_configured_for_graph_tasks", extra={"error": str(exc)})
        return _DummyTaskApp()


task_app = _resolve_task_app()


@task_app.task(
    bind=True,
    autoretry_for=TRANSIENT_EXCEPTIONS,
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=4,
    name="tasks.build_graph_task",
)
def build_graph_task(
    self,
    chunks_data: list[dict[str, Any]],
    document_id: str | None = None,
) -> dict[str, Any]:
    """Build knowledge graph from chunk payloads."""
    task_id = getattr(getattr(self, "request", None), "id", None)
    logger.info(
        "build_graph_task_started",
        extra={"task_id": task_id, "document_id": document_id, "chunk_count": len(chunks_data)},
    )

    if not chunks_data:
        raise IngestionValidationError("chunks_data must not be empty")

    chunks = [DocumentChunk.model_validate(item) for item in chunks_data]
    pipeline = KnowledgeGraphPipeline()
    resolved_document_id = document_id or str(chunks[0].document_id)

    result = pipeline.build_for_document(document_id=resolved_document_id, chunks=chunks)
    payload = {
        "status": result.get("status", "failed"),
        "document_id": result.get("document_id", resolved_document_id),
        "chunk_count": len(chunks),
        "entity_count": result.get("entity_count", 0),
        "relation_count": result.get("relation_count", 0),
        "errors": result.get("errors", []),
    }
    logger.info(
        "build_graph_task_completed",
        extra={
            "task_id": task_id,
            "document_id": payload["document_id"],
            "status": payload["status"],
            "entity_count": payload["entity_count"],
            "relation_count": payload["relation_count"],
        },
    )
    return payload


async def run_graph_job(document_id: UUID) -> None:
    """Backward-compatible placeholder for older imports."""
    _ = document_id
