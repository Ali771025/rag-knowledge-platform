from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.admin.common_auth import require_admin_token
from app.api.deps import get_db_session
from app.core.token_monitoring_guard import token_monitoring_tables_ready
from app.models.user import User
from app.schemas.token_optimization import (
    OptimizationRecommendationItem,
    OptimizationRecommendationListResponse,
    OptimizationSavingsReportResponse,
    RecommendationDismissResponse,
    SavingsByCategory,
)
from app.services.token_optimization_service import TokenOptimizationService

router = APIRouter(prefix="/admin/optimization", tags=["admin-token-optimization"])


def _ensure_token_monitoring_schema_ready(db: Session) -> None:
    if token_monitoring_tables_ready(db):
        return
    raise HTTPException(
        status_code=503,
        detail=(
            "Token monitoring schema is not initialized. "
            "Run Alembic migrations (target revision: b1c2d3e4f5a6)."
        ),
    )


@router.get("/recommendations", response_model=OptimizationRecommendationListResponse)
def get_recommendations(
    _admin: Annotated[User, Depends(require_admin_token)],
    db: Annotated[Session, Depends(get_db_session)],
    include_dismissed: bool = False,
    limit: int = Query(default=200, ge=1, le=1000),
) -> OptimizationRecommendationListResponse:
    _ensure_token_monitoring_schema_ready(db)
    service = TokenOptimizationService(db)
    records = service.list_recommendations(include_dismissed=include_dismissed, limit=limit)

    return OptimizationRecommendationListResponse(
        items=[
            OptimizationRecommendationItem(
                id=item.id,
                api_key_id=item.api_key_id,
                category=item.category,
                severity=item.severity,
                title=item.title,
                description=item.description or item.summary,
                potential_saving_usd=item.potential_saving_usd,
                action_items=list(item.action_items_json or []),
                generated_at=item.generated_at,
                is_dismissed=item.is_dismissed,
                dismissed_at=item.dismissed_at,
                metadata=dict(item.payload_json or {}),
            )
            for item in records
        ]
    )


@router.post("/dismiss/{recommendation_id}", response_model=RecommendationDismissResponse)
def dismiss_recommendation(
    recommendation_id: UUID,
    _admin: Annotated[User, Depends(require_admin_token)],
    db: Annotated[Session, Depends(get_db_session)],
) -> RecommendationDismissResponse:
    _ensure_token_monitoring_schema_ready(db)
    service = TokenOptimizationService(db)
    try:
        record = service.dismiss_recommendation(recommendation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return RecommendationDismissResponse(
        id=record.id,
        is_dismissed=record.is_dismissed,
        dismissed_at=record.dismissed_at,
    )


@router.get("/savings-report", response_model=OptimizationSavingsReportResponse)
def get_savings_report(
    _admin: Annotated[User, Depends(require_admin_token)],
    db: Annotated[Session, Depends(get_db_session)],
) -> OptimizationSavingsReportResponse:
    _ensure_token_monitoring_schema_ready(db)
    service = TokenOptimizationService(db)
    total, by_category, high_priority = service.savings_report()
    return OptimizationSavingsReportResponse(
        total_potential_monthly_savings_usd=total,
        savings_by_category=[
            SavingsByCategory(category=category, potential_saving_usd=value)
            for category, value in by_category.items()
        ],
        high_priority_recommendation_count=high_priority,
    )
