from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Iterable
import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.token_monitoring import APIKeyMetadata, BudgetAlert, BudgetChangeAuditLog
from app.models.token_monitoring import TokenUsageLog
from app.repositories.token_monitoring_repository import (
    APIKeyBudgetConfigRepository,
    BudgetAlertRepository,
    BudgetChangeAuditRepository,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BudgetCycleWindow:
    start_date: date
    end_date: date
    start_at: datetime
    next_cycle_start_at: datetime
    period_key: str


class TokenBudgetService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.budget_configs = APIKeyBudgetConfigRepository(db)
        self.alerts = BudgetAlertRepository(db)
        self.audit_logs = BudgetChangeAuditRepository(db)

    @staticmethod
    def normalize_thresholds(thresholds: Iterable[int]) -> list[int]:
        values = [int(value) for value in thresholds]
        if not values:
            raise ValueError("alert_thresholds must not be empty")
        if values != sorted(values):
            raise ValueError("alert_thresholds must be sorted in ascending order")
        if len(values) != len(set(values)):
            raise ValueError("alert_thresholds must be unique")
        for value in values:
            if value < 1 or value > 100:
                raise ValueError("alert_thresholds values must be between 1 and 100")
        return values

    def update_budget_config(
        self,
        *,
        api_key_id: UUID,
        actor_user_id: UUID,
        monthly_budget_usd: Decimal | None,
        alert_thresholds: list[int],
    ):
        api_key = self.db.get(APIKeyMetadata, api_key_id)
        if api_key is None:
            raise ValueError("API key not found")

        if monthly_budget_usd is not None and monthly_budget_usd <= Decimal("0"):
            raise ValueError("monthly_budget_usd must be greater than zero")

        normalized_thresholds = self.normalize_thresholds(alert_thresholds)
        existing = self.budget_configs.get_by_api_key_id(api_key_id)

        old_budget = existing.monthly_budget_usd if existing is not None else None
        old_thresholds = list(existing.alert_thresholds_json) if existing is not None else []

        config = self.budget_configs.upsert(
            api_key_id=api_key_id,
            monthly_budget_usd=monthly_budget_usd,
            alert_thresholds=normalized_thresholds,
        )

        audit = BudgetChangeAuditLog(
            api_key_id=api_key_id,
            changed_by_user_id=actor_user_id,
            old_monthly_budget_usd=old_budget,
            new_monthly_budget_usd=monthly_budget_usd,
            old_alert_thresholds_json=old_thresholds,
            new_alert_thresholds_json=normalized_thresholds,
            metadata_json={"source": "admin_api"},
        )
        self.audit_logs.create(audit)
        logger.info(
            "token_budget.updated",
            extra={
                "api_key_id": str(api_key_id),
                "actor_user_id": str(actor_user_id),
                "old_monthly_budget_usd": str(old_budget) if old_budget is not None else None,
                "new_monthly_budget_usd": str(monthly_budget_usd) if monthly_budget_usd is not None else None,
                "old_thresholds": old_thresholds,
                "new_thresholds": normalized_thresholds,
            },
        )

        return config

    def list_active_alerts(self, *, limit: int = 200) -> list[BudgetAlert]:
        return self.alerts.list_active(limit=limit)

    def evaluate_threshold_crossings(
        self,
        *,
        api_key_id: UUID,
        at_time: datetime | None = None,
    ) -> list[BudgetAlert]:
        config = self.budget_configs.get_by_api_key_id(api_key_id)
        if config is None or config.monthly_budget_usd is None or config.monthly_budget_usd <= Decimal("0"):
            return []

        moment = at_time or datetime.now(UTC)
        cycle = self._monthly_cycle_window(moment)
        current_spend = self._current_spend(
            api_key_id=api_key_id,
            start_at=cycle.start_at,
            end_at=cycle.next_cycle_start_at,
        )

        created_alerts: list[BudgetAlert] = []
        for threshold_percent in self.normalize_thresholds(config.alert_thresholds_json):
            threshold_usd = (config.monthly_budget_usd * Decimal(threshold_percent) / Decimal(100)).quantize(
                Decimal("0.000000001")
            )
            if current_spend < threshold_usd:
                continue

            if self.alerts.exists_for_cycle_threshold(
                api_key_id=api_key_id,
                cycle_start=cycle.start_date,
                threshold_percent=threshold_percent,
            ):
                continue

            alert = BudgetAlert(
                api_key_id=api_key_id,
                threshold_usd=threshold_usd,
                threshold_percent=threshold_percent,
                current_spend_usd=current_spend,
                budget_usd=config.monthly_budget_usd,
                period="monthly",
                cycle_start=cycle.start_date,
                cycle_end=cycle.end_date,
                status="active",
                metadata_json={
                    "threshold_percent": threshold_percent,
                    "period_key": cycle.period_key,
                },
            )
            try:
                created = self.alerts.create(alert)
                created_alerts.append(created)
                logger.info(
                    "token_budget.alert_created",
                    extra={
                        "api_key_id": str(api_key_id),
                        "threshold_percent": threshold_percent,
                        "threshold_usd": str(threshold_usd),
                        "current_spend_usd": str(current_spend),
                        "budget_usd": str(config.monthly_budget_usd),
                        "period_key": cycle.period_key,
                    },
                )
            except IntegrityError:
                # Concurrent writers may race. Unique constraint ensures one alert is created.
                self.db.rollback()

        return created_alerts

    def _current_spend(self, *, api_key_id: UUID, start_at: datetime, end_at: datetime) -> Decimal:
        spend_stmt = select(func.coalesce(func.sum(TokenUsageLog.cost_usd), Decimal("0"))).where(
            TokenUsageLog.api_key_id == api_key_id,
            TokenUsageLog.created_at >= start_at,
            TokenUsageLog.created_at < end_at,
        )
        value = self.db.scalar(spend_stmt)
        return Decimal(str(value or Decimal("0")))

    @staticmethod
    def _monthly_cycle_window(moment: datetime) -> BudgetCycleWindow:
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        else:
            moment = moment.astimezone(UTC)
        start_date = date(moment.year, moment.month, 1)
        if moment.month == 12:
            next_cycle_start = datetime(moment.year + 1, 1, 1, tzinfo=UTC)
        else:
            next_cycle_start = datetime(moment.year, moment.month + 1, 1, tzinfo=UTC)

        end_date = next_cycle_start.date() - timedelta(days=1)
        start_at = datetime(moment.year, moment.month, 1, tzinfo=UTC)
        period_key = f"{start_date.year:04d}-{start_date.month:02d}"

        return BudgetCycleWindow(
            start_date=start_date,
            end_date=end_date,
            start_at=start_at,
            next_cycle_start_at=next_cycle_start,
            period_key=period_key,
        )
