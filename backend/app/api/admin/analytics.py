"""Internal admin analytics summary endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.admin.common_auth import require_admin_token
from app.models.user import User
from app.core.database import SessionLocal
from app.observability.analytics_summary_service import AnalyticsSummaryService
from app.repositories.conversation_log_repository import ConversationLogRepository
from app.repositories.cost_log_repository import CostLogRepository
from app.repositories.session_log_repository import SessionLogRepository
from app.schemas.analytics import AnalyticsSummaryResponse

router = APIRouter(prefix="/admin/metrics", tags=["admin-metrics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_metrics_summary(_admin: User = Depends(require_admin_token)) -> AnalyticsSummaryResponse:
    db = SessionLocal()
    try:
        service = AnalyticsSummaryService(
            conversation_logs=ConversationLogRepository(db),
            cost_logs=CostLogRepository(db),
            session_logs=SessionLogRepository(db),
        )
        summary = service.get_today_summary()

        return AnalyticsSummaryResponse(
            requests_today=summary.requests_today,
            active_sessions=summary.active_sessions,
            avg_latency_ms=summary.avg_latency_ms,
            p95_latency_ms=summary.p95_latency_ms,
            total_tokens_today=summary.total_tokens_today,
            total_cost_today=summary.total_cost_today,
            state_distribution=dict(summary.state_distribution),
        )
    finally:
        db.close()
