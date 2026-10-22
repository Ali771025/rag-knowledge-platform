from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.token_monitoring import (
    APIKeyMetadata,
    APIKeyBudgetConfig,
    BudgetAlert,
    BudgetChangeAuditLog,
    DailyAggregate,
    OptimizationRecommendation,
    TokenProvider,
    TokenUsageLog,
)


class APIKeyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        provider: TokenProvider,
        display_name: str,
        key_alias: str | None,
        key_fingerprint: str,
        key_hash: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> APIKeyMetadata:
        record = APIKeyMetadata(
            provider=provider,
            display_name=display_name,
            key_alias=key_alias,
            key_fingerprint=key_fingerprint,
            key_hash=key_hash,
            metadata_json=metadata_json or {},
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_by_id(self, api_key_id: UUID) -> APIKeyMetadata | None:
        return self.db.get(APIKeyMetadata, api_key_id)

    def get_by_fingerprint(self, key_fingerprint: str) -> APIKeyMetadata | None:
        stmt = select(APIKeyMetadata).where(APIKeyMetadata.key_fingerprint == key_fingerprint)
        return self.db.scalar(stmt)

    def list_active(self, provider: TokenProvider | None = None) -> list[APIKeyMetadata]:
        stmt = select(APIKeyMetadata).where(APIKeyMetadata.is_active.is_(True))
        if provider is not None:
            stmt = stmt.where(APIKeyMetadata.provider == provider)
        stmt = stmt.order_by(APIKeyMetadata.created_at.desc())
        return list(self.db.scalars(stmt).all())


class TokenUsageLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        api_key_id: UUID,
        provider: TokenProvider,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost_usd: Decimal,
        request_id: str | None = None,
        latency_ms: int = 0,
        cache_hit: bool = False,
        endpoint: str | None = None,
        session_id: str | None = None,
        metadata_json: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> TokenUsageLog:
        log = TokenUsageLog(
            api_key_id=api_key_id,
            provider=provider,
            model_name=model_name,
            prompt_tokens=max(prompt_tokens, 0),
            completion_tokens=max(completion_tokens, 0),
            total_tokens=max(total_tokens, 0),
            cost_usd=max(cost_usd, Decimal("0")),
            request_id=request_id,
            latency_ms=max(int(latency_ms), 0),
            cache_hit=bool(cache_hit),
            endpoint=endpoint,
            session_id=session_id,
            metadata_json=metadata_json or {},
            created_at=created_at or datetime.now(timezone.utc),
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log


class DailyAggregateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_api_key(
        self,
        *,
        api_key_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[DailyAggregate]:
        stmt = select(DailyAggregate).where(DailyAggregate.api_key_id == api_key_id)
        if start_date is not None:
            stmt = stmt.where(DailyAggregate.date >= start_date)
        if end_date is not None:
            stmt = stmt.where(DailyAggregate.date <= end_date)
        stmt = stmt.order_by(DailyAggregate.date.desc())
        return list(self.db.scalars(stmt).all())

    def aggregate_cost(
        self,
        *,
        api_key_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Decimal:
        stmt: Select[tuple[Any]] = select(func.coalesce(func.sum(DailyAggregate.total_cost_usd), Decimal("0"))).where(
            DailyAggregate.api_key_id == api_key_id
        )
        if start_date is not None:
            stmt = stmt.where(DailyAggregate.date >= start_date)
        if end_date is not None:
            stmt = stmt.where(DailyAggregate.date <= end_date)
        total = self.db.scalar(stmt)
        return Decimal(str(total or Decimal("0")))


class OptimizationRecommendationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, recommendation: OptimizationRecommendation) -> OptimizationRecommendation:
        self.db.add(recommendation)
        self.db.commit()
        self.db.refresh(recommendation)
        return recommendation

    def list_recommendations(self, *, include_dismissed: bool = False, limit: int = 200) -> list[OptimizationRecommendation]:
        stmt = select(OptimizationRecommendation)
        if not include_dismissed:
            stmt = stmt.where(OptimizationRecommendation.is_dismissed.is_(False))
        stmt = stmt.order_by(OptimizationRecommendation.generated_at.desc()).limit(max(limit, 1))
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, recommendation_id: UUID) -> OptimizationRecommendation | None:
        return self.db.get(OptimizationRecommendation, recommendation_id)

    def dismiss(self, recommendation: OptimizationRecommendation) -> OptimizationRecommendation:
        recommendation.is_dismissed = True
        recommendation.dismissed_at = datetime.now(timezone.utc)
        self.db.add(recommendation)
        self.db.commit()
        self.db.refresh(recommendation)
        return recommendation

    def exists_recent_dedupe(self, *, dedupe_key: str, created_after: datetime) -> bool:
        if not dedupe_key:
            return False
        stmt = select(func.count()).select_from(OptimizationRecommendation).where(
            OptimizationRecommendation.dedupe_key == dedupe_key,
            OptimizationRecommendation.generated_at >= created_after,
            OptimizationRecommendation.is_dismissed.is_(False),
        )
        return bool(self.db.scalar(stmt) or 0)


class BudgetAlertRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, alert: BudgetAlert) -> BudgetAlert:
        self.db.add(alert)
        try:
            self.db.commit()
            self.db.refresh(alert)
        except IntegrityError:
            self.db.rollback()
            raise
        return alert

    def exists_for_cycle_threshold(
        self,
        *,
        api_key_id: UUID,
        cycle_start: date,
        threshold_percent: int,
    ) -> bool:
        stmt = select(func.count()).select_from(BudgetAlert).where(
            BudgetAlert.api_key_id == api_key_id,
            BudgetAlert.cycle_start == cycle_start,
            BudgetAlert.threshold_percent == threshold_percent,
        )
        return bool(self.db.scalar(stmt) or 0)

    def list_active(self, *, limit: int = 200) -> list[BudgetAlert]:
        stmt = (
            select(BudgetAlert)
            .where(BudgetAlert.status == "active")
            .order_by(BudgetAlert.triggered_at.desc())
            .limit(max(limit, 1))
        )
        return list(self.db.scalars(stmt).all())


class APIKeyBudgetConfigRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_api_key_id(self, api_key_id: UUID) -> APIKeyBudgetConfig | None:
        stmt = select(APIKeyBudgetConfig).where(APIKeyBudgetConfig.api_key_id == api_key_id)
        return self.db.scalar(stmt)

    def upsert(
        self,
        *,
        api_key_id: UUID,
        monthly_budget_usd: Decimal | None,
        alert_thresholds: list[int],
    ) -> APIKeyBudgetConfig:
        config = self.get_by_api_key_id(api_key_id)
        if config is None:
            config = APIKeyBudgetConfig(
                api_key_id=api_key_id,
                monthly_budget_usd=monthly_budget_usd,
                alert_thresholds_json=alert_thresholds,
            )
        else:
            config.monthly_budget_usd = monthly_budget_usd
            config.alert_thresholds_json = alert_thresholds
            config.updated_at = datetime.now(timezone.utc)

        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config


class BudgetChangeAuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, record: BudgetChangeAuditLog) -> BudgetChangeAuditLog:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
