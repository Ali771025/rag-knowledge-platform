from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.admin.common_auth import require_admin_token
from app.api.deps import get_db_session
from app.core.token_monitoring_guard import token_monitoring_tables_ready
from app.models.token_monitoring import APIKeyBudgetConfig, APIKeyMetadata, TokenProvider, TokenUsageLog
from app.models.user import User
from app.schemas.token_budgeting import (
    APIKeyBudgetConfigResponse,
    APIKeyListItem,
    APIKeyListResponse,
    ActiveBudgetAlertItem,
    ActiveBudgetAlertsResponse,
    BudgetUpdateRequest,
)
from app.services.token_budget_service import TokenBudgetService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-token-budget"])


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


@router.get("/api-keys", response_model=APIKeyListResponse)
def list_api_keys(
    _admin: Annotated[User, Depends(require_admin_token)],
    db: Annotated[Session, Depends(get_db_session)],
    search: str | None = Query(default=None, min_length=1, max_length=64),
    provider: TokenProvider | None = None,
    is_active: bool | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
) -> APIKeyListResponse:
    _ensure_token_monitoring_schema_ready(db)
    now = datetime.now(UTC)
    month_start = datetime(now.year, now.month, 1, tzinfo=UTC)

    keys_stmt = select(APIKeyMetadata)
    if provider is not None:
        keys_stmt = keys_stmt.where(APIKeyMetadata.provider == provider)
    if is_active is not None:
        keys_stmt = keys_stmt.where(APIKeyMetadata.is_active.is_(is_active))
    if search:
        pattern = f"%{search.lower()}%"
        keys_stmt = keys_stmt.where(
            func.lower(APIKeyMetadata.display_name).like(pattern)
            | func.lower(func.coalesce(APIKeyMetadata.key_alias, "")).like(pattern)
            | func.lower(APIKeyMetadata.key_fingerprint).like(pattern)
        )
    keys = list(db.scalars(keys_stmt.order_by(APIKeyMetadata.created_at.desc()).limit(limit)).all())

    items: list[APIKeyListItem] = []
    for key in keys:
        budget_config = db.scalar(select(APIKeyBudgetConfig).where(APIKeyBudgetConfig.api_key_id == key.id))
        spend = db.scalar(
            select(func.coalesce(func.sum(TokenUsageLog.cost_usd), 0)).where(
                TokenUsageLog.api_key_id == key.id,
                TokenUsageLog.created_at >= month_start,
                TokenUsageLog.created_at <= now,
            )
        )
        last_used_at = db.scalar(
            select(func.max(TokenUsageLog.created_at)).where(
                TokenUsageLog.api_key_id == key.id,
            )
        )

        items.append(
            APIKeyListItem(
                id=key.id,
                display_name=key.display_name,
                key_alias=key.key_alias,
                provider=key.provider.value,
                is_active=key.is_active,
                key_fingerprint=key.key_fingerprint,
                monthly_budget_usd=budget_config.monthly_budget_usd if budget_config else None,
                alert_thresholds=list(budget_config.alert_thresholds_json or []) if budget_config else [],
                current_month_spend_usd=spend or 0,
                last_used_at=last_used_at,
            )
        )
    return APIKeyListResponse(items=items)


@router.put("/api-keys/{api_key_id}/budget", response_model=APIKeyBudgetConfigResponse)
def update_api_key_budget(
    api_key_id: UUID,
    payload: BudgetUpdateRequest,
    admin: Annotated[User, Depends(require_admin_token)],
    db: Annotated[Session, Depends(get_db_session)],
) -> APIKeyBudgetConfigResponse:
    _ensure_token_monitoring_schema_ready(db)
    service = TokenBudgetService(db)
    try:
        config = service.update_budget_config(
            api_key_id=api_key_id,
            actor_user_id=admin.id,
            monthly_budget_usd=payload.monthly_budget_usd,
            alert_thresholds=payload.alert_thresholds,
        )
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail.lower():
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=422, detail=detail) from exc
    logger.info(
        "token_budget.api_updated",
        extra={
            "api_key_id": str(api_key_id),
            "admin_user_id": str(admin.id),
            "threshold_count": len(payload.alert_thresholds),
        },
    )

    return APIKeyBudgetConfigResponse(
        api_key_id=config.api_key_id,
        monthly_budget_usd=config.monthly_budget_usd,
        alert_thresholds=list(config.alert_thresholds_json),
        updated_at=config.updated_at,
    )


@router.get("/alerts/active", response_model=ActiveBudgetAlertsResponse)
def get_active_budget_alerts(
    _admin: Annotated[User, Depends(require_admin_token)],
    db: Annotated[Session, Depends(get_db_session)],
    limit: int = Query(default=200, ge=1, le=500),
) -> ActiveBudgetAlertsResponse:
    _ensure_token_monitoring_schema_ready(db)
    service = TokenBudgetService(db)
    alerts = service.list_active_alerts(limit=limit)

    items: list[ActiveBudgetAlertItem] = []
    for alert in alerts:
        api_key = db.get(APIKeyMetadata, alert.api_key_id)
        if api_key is None:
            continue
        threshold_percent = int(alert.threshold_percent or int((alert.metadata_json or {}).get("threshold_percent", 0) or 0))
        items.append(
            ActiveBudgetAlertItem(
                id=alert.id,
                api_key_id=alert.api_key_id,
                key_alias=api_key.key_alias,
                provider=api_key.provider.value,
                threshold_percent=threshold_percent,
                threshold_usd=alert.threshold_usd,
                current_spend_usd=alert.current_spend_usd,
                budget_usd=alert.budget_usd,
                triggered_at=alert.triggered_at,
                status=alert.status,
                cycle_start=alert.cycle_start,
                cycle_end=alert.cycle_end,
                metadata=dict(alert.metadata_json or {}),
            )
        )
    logger.debug("token_budget.active_alerts_listed", extra={"alert_count": len(items)})

    return ActiveBudgetAlertsResponse(items=items)
