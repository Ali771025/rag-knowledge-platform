"""Task management API endpoints.

Routes remain thin and delegate queue orchestration/status concerns to task
modules and task-tracker services.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.security import get_current_user, require_role
from app.models.user import User
from app.services.tasks.task_tracker import TaskTracker
from app.tasks.knowledge import batch_embed_documents, process_document_async, rebuild_knowledge_graph
from app.tasks.memory import summarize_conversation_memory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])
_task_tracker = TaskTracker(allow_terminate=False)


class KnowledgeProcessRequest(BaseModel):
    document_id: str = Field(min_length=1, max_length=100)
    document_content: str = Field(min_length=1, max_length=2_000_000)
    document_metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class GraphRebuildRequest(BaseModel):
    scope: str = Field(default="incremental", min_length=1, max_length=32)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class VectorReindexRequest(BaseModel):
    document_ids: list[str] = Field(min_length=1, max_length=1000)
    force_reindex: bool = True

    model_config = ConfigDict(extra="forbid")


class MemorySummarizeRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    conversation_messages: list[dict[str, Any]] = Field(default_factory=list, max_length=5000)

    model_config = ConfigDict(extra="forbid")


class TaskEnqueueResponse(BaseModel):
    task_id: str
    state: str = "PENDING"
    task_name: str
    message: str


def _enqueue_task(task_callable: Any, *args: Any, **kwargs: Any) -> TaskEnqueueResponse:
    delay_fn = getattr(task_callable, "delay", None)
    if not callable(delay_fn):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Background worker is unavailable",
        )

    try:
        result = delay_fn(*args, **kwargs)
    except Exception as exc:
        logger.exception("task_enqueue_failed", extra={"task_name": getattr(task_callable, "name", None)}, exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to enqueue task") from exc

    task_id = str(getattr(result, "id", "") or "").strip()
    if not task_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Task queue did not return task id")

    task_name = str(getattr(task_callable, "name", "unknown_task"))
    return TaskEnqueueResponse(
        task_id=task_id,
        state="PENDING",
        task_name=task_name,
        message="Task accepted",
    )


@router.post("/knowledge/process", response_model=TaskEnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
def enqueue_knowledge_process(
    payload: KnowledgeProcessRequest,
    current_user: User = Depends(get_current_user),
) -> TaskEnqueueResponse:
    """Enqueue one knowledge document-processing task."""
    logger.info(
        "enqueue_knowledge_process_requested",
        extra={"user_id": str(current_user.id), "document_id": payload.document_id},
    )
    return _enqueue_task(
        process_document_async,
        payload.document_id,
        payload.document_content,
        payload.document_metadata,
    )


@router.post("/knowledge/rebuild-graph", response_model=TaskEnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
def enqueue_graph_rebuild(
    payload: GraphRebuildRequest,
    admin_user: User = Depends(require_role("admin")),
) -> TaskEnqueueResponse:
    """Enqueue graph rebuild task (admin-only)."""
    logger.info(
        "enqueue_graph_rebuild_requested",
        extra={"admin_user_id": str(admin_user.id), "scope": payload.scope},
    )
    return _enqueue_task(rebuild_knowledge_graph, payload.scope)


@router.post("/knowledge/reindex-vectors", response_model=TaskEnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
def enqueue_vector_reindex(
    payload: VectorReindexRequest,
    admin_user: User = Depends(require_role("admin")),
) -> TaskEnqueueResponse:
    """Enqueue vector re-index task for existing documents (admin-only)."""
    logger.info(
        "enqueue_vector_reindex_requested",
        extra={"admin_user_id": str(admin_user.id), "document_count": len(payload.document_ids), "force_reindex": payload.force_reindex},
    )
    return _enqueue_task(batch_embed_documents, payload.document_ids, payload.force_reindex)


@router.post("/memory/summarize", response_model=TaskEnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
def enqueue_memory_summarize(
    payload: MemorySummarizeRequest,
    current_user: User = Depends(get_current_user),
) -> TaskEnqueueResponse:
    """Enqueue memory summarization task for a session."""
    logger.info(
        "enqueue_memory_summarize_requested",
        extra={"user_id": str(current_user.id), "session_id": payload.session_id},
    )
    return _enqueue_task(summarize_conversation_memory, payload.session_id, payload.conversation_messages)


@router.get("/{task_id}", status_code=status.HTTP_200_OK)
def get_task_status(task_id: str, current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Return normalized task status payload for one task id."""
    logger.info("task_status_requested", extra={"user_id": str(current_user.id), "task_id": task_id})
    return _task_tracker.get_task_status(task_id)


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
def cancel_task(task_id: str, current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Request cancellation for a queued/running task."""
    logger.info("task_cancel_requested", extra={"user_id": str(current_user.id), "task_id": task_id})
    return _task_tracker.cancel_task(task_id)
