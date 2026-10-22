"""Admin cost endpoints for usage and budget visibility."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.admin.common_auth import require_admin_token
from app.core.runtime_services import get_runtime_services
from app.models.llm.contracts import CostSummarySnapshot
from app.models.user import User
from app.services.cost.budget_guard import BudgetDecision

router = APIRouter(prefix="/admin/cost", tags=["admin-cost"])


class CostSummaryResponse(BaseModel):
    """Typed admin cost summary payload."""

    daily: CostSummarySnapshot
    monthly: CostSummarySnapshot
    cache_saved_cost_usd_daily: float = Field(default=0.0, ge=0.0)
    budget_decision: BudgetDecision
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")


@router.get("/summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    _admin: Annotated[User, Depends(require_admin_token)],
    user_id: str | None = None,
    session_id: str | None = None,
) -> CostSummaryResponse:
    """Return daily/monthly spend summaries plus active budget mode decision."""
    services = get_runtime_services()
    now = datetime.now(timezone.utc)
    daily_start = now - timedelta(days=1)
    monthly_start = now - timedelta(days=30)

    daily = await services.cost_tracker.get_summary(
        window_start=daily_start,
        window_end=now,
        user_id=user_id,
        session_id=session_id,
    )
    monthly = await services.cost_tracker.get_summary(
        window_start=monthly_start,
        window_end=now,
        user_id=user_id,
        session_id=session_id,
    )
    cache_saved_daily = await services.cost_tracker.get_cache_savings(
        window_start=daily_start,
        window_end=now,
        user_id=user_id,
        session_id=session_id,
    )
    budget_decision = await services.budget_guard.evaluate_budget(
        daily_snapshot=daily,
        monthly_snapshot=monthly,
    )
    return CostSummaryResponse(
        daily=daily,
        monthly=monthly,
        cache_saved_cost_usd_daily=cache_saved_daily,
        budget_decision=budget_decision,
    )


__all__ = ["router", "CostSummaryResponse"]
