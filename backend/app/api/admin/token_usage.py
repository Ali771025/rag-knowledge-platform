from __future__ import annotations

from datetime import datetime
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.admin.common_auth import require_admin_token
from app.api.deps import get_db_session
from app.core.token_monitoring_guard import token_monitoring_tables_ready
from app.models.token_monitoring import TokenProvider
from app.models.user import User
from app.schemas.token_usage_analytics import (
    APIKeyUsageDetailsResponse,
    CostForecastResponse,
    TokenUsageByModelResponse,
    TokenUsageSummaryResponse,
)
from app.services.token_usage_analytics import TokenUsageAnalyticsService, TokenUsageFilter
from app.services.token_usage_stream import token_usage_realtime_stream_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/token-usage", tags=["admin-token-usage"])


def _build_filters(
    *,
    provider: TokenProvider | None,
    model: str | None,
    api_key_id: UUID | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> TokenUsageFilter:
    return TokenUsageFilter(
        provider=provider.value if provider is not None else None,
        model=model,
        api_key_id=api_key_id,
        date_from=date_from,
        date_to=date_to,
    )


def _validate_date_range(*, date_from: datetime | None, date_to: datetime | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must be less than or equal to date_to")


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


@router.get("/summary", response_model=TokenUsageSummaryResponse)
def get_token_usage_summary(
    _admin: Annotated[User, Depends(require_admin_token)],
    db: Annotated[Session, Depends(get_db_session)],
    provider: TokenProvider | None = None,
    model: str | None = Query(default=None, min_length=1, max_length=128),
    api_key_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    granularity: str = Query(default="daily", pattern="^(hourly|daily|weekly|monthly)$"),
) -> TokenUsageSummaryResponse:
    _ensure_token_monitoring_schema_ready(db)
    _validate_date_range(date_from=date_from, date_to=date_to)
    service = TokenUsageAnalyticsService(db)
    filters = _build_filters(
        provider=provider,
        model=model,
        api_key_id=api_key_id,
        date_from=date_from,
        date_to=date_to,
    )
    return service.summary(filters=filters, granularity=granularity)


@router.get("/by-model", response_model=TokenUsageByModelResponse)
def get_token_usage_by_model(
    _admin: Annotated[User, Depends(require_admin_token)],
    db: Annotated[Session, Depends(get_db_session)],
    provider: TokenProvider | None = None,
    model: str | None = Query(default=None, min_length=1, max_length=128),
    api_key_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> TokenUsageByModelResponse:
    _ensure_token_monitoring_schema_ready(db)
    _validate_date_range(date_from=date_from, date_to=date_to)
    service = TokenUsageAnalyticsService(db)
    filters = _build_filters(
        provider=provider,
        model=model,
        api_key_id=api_key_id,
        date_from=date_from,
        date_to=date_to,
    )
    return service.by_model(filters=filters)


@router.get("/by-key/{api_key_id}", response_model=APIKeyUsageDetailsResponse)
def get_token_usage_by_key(
    api_key_id: UUID,
    _admin: Annotated[User, Depends(require_admin_token)],
    db: Annotated[Session, Depends(get_db_session)],
    provider: TokenProvider | None = None,
    model: str | None = Query(default=None, min_length=1, max_length=128),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    granularity: str = Query(default="daily", pattern="^(hourly|daily|weekly|monthly)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> APIKeyUsageDetailsResponse:
    _ensure_token_monitoring_schema_ready(db)
    _validate_date_range(date_from=date_from, date_to=date_to)
    service = TokenUsageAnalyticsService(db)
    filters = _build_filters(
        provider=provider,
        model=model,
        api_key_id=api_key_id,
        date_from=date_from,
        date_to=date_to,
    )
    try:
        return service.by_key(
            api_key_id=api_key_id,
            filters=filters,
            granularity=granularity,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/cost-forecast", response_model=CostForecastResponse)
def get_cost_forecast(
    _admin: Annotated[User, Depends(require_admin_token)],
    db: Annotated[Session, Depends(get_db_session)],
    provider: TokenProvider | None = None,
    model: str | None = Query(default=None, min_length=1, max_length=128),
    api_key_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> CostForecastResponse:
    _ensure_token_monitoring_schema_ready(db)
    _validate_date_range(date_from=date_from, date_to=date_to)
    service = TokenUsageAnalyticsService(db)
    filters = _build_filters(
        provider=provider,
        model=model,
        api_key_id=api_key_id,
        date_from=date_from,
        date_to=date_to,
    )
    return service.forecast(filters=filters)


@router.get("/realtime")
async def get_token_usage_realtime(
    _admin: Annotated[User, Depends(require_admin_token)],
    db: Annotated[Session, Depends(get_db_session)],
):
    _ensure_token_monitoring_schema_ready(db)
    logger.debug("token_usage.realtime_stream_opened")
    return StreamingResponse(
        token_usage_realtime_stream_service.stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
