"""Admin LLM endpoints for usage and routing visibility."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.admin.common_auth import require_admin_token
from app.models.user import User
from app.core.runtime_services import get_runtime_services

router = APIRouter(prefix="/admin/llm", tags=["admin-llm"])


class LLMUsageResponse(BaseModel):
    """Typed LLM admin usage payload."""

    metrics: dict[str, float]
    recent_usage_records: list[dict[str, Any]]
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")


@router.get("/usage", response_model=LLMUsageResponse)
async def get_llm_usage(
    _admin: Annotated[User, Depends(require_admin_token)],
    user_id: str | None = None,
    session_id: str | None = None,
    limit: int = 50,
) -> LLMUsageResponse:
    """Return in-process LLM metrics and recent tracked usage records."""
    services = get_runtime_services()
    records = await services.cost_tracker.list_records(user_id=user_id, session_id=session_id)
    serialized = [entry.model_dump(mode="json") for entry in records[-max(limit, 1) :]]
    return LLMUsageResponse(
        metrics=services.llm_metrics.snapshot(),
        recent_usage_records=serialized,
    )


__all__ = ["router", "LLMUsageResponse"]
