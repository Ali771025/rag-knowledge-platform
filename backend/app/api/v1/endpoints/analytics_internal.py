"""Internal analytics endpoints for funnel and trigger outcomes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.repositories import ConversionAnalyticsRepository, TriggerEffectivenessRepository
from app.analytics.service import AnalyticsInsightsService
from app.core.database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _build_service(db: Session) -> AnalyticsInsightsService:
    return AnalyticsInsightsService(
        conversion_repo=ConversionAnalyticsRepository(db),
        trigger_repo=TriggerEffectivenessRepository(db),
    )


@router.get("/funnel-summary")
def funnel_summary(db: Session = Depends(get_db)) -> dict[str, object]:
    service = _build_service(db)
    return {
        "conversion_rate_by_persona": service.conversion_rate_by_persona(),
        "funnel_dropout_by_stage": service.funnel_dropout_by_stage(),
    }


@router.get("/trigger-performance")
def trigger_performance(
    stage: str = Query(..., min_length=1, max_length=64),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    service = _build_service(db)
    return {"stage": stage, "results": service.trigger_performance_by_stage(stage)}


@router.get("/persona-conversion")
def persona_conversion(db: Session = Depends(get_db)) -> dict[str, object]:
    service = _build_service(db)
    return {"conversion_rate_by_persona": service.conversion_rate_by_persona()}
