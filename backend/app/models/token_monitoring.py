from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TokenProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"


class RecommendationCategory(str, Enum):
    COST = "cost"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    CACHING = "caching"


class RecommendationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [str(item.value) for item in enum_cls]


class APIKeyMetadata(Base):
    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider: Mapped[TokenProvider] = mapped_column(
        SqlEnum(
            TokenProvider,
            name="token_provider_enum",
            native_enum=True,
            values_callable=_enum_values,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_alias: Mapped[str | None] = mapped_column(String(32), nullable=True)
    key_fingerprint: Mapped[str] = mapped_column(String(24), nullable=False, unique=True, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class TokenUsageLog(Base):
    __tablename__ = "token_usage_logs"
    __table_args__ = (
        Index("ix_token_usage_logs_created_at", "created_at"),
        Index("ix_token_usage_logs_api_key_id", "api_key_id"),
        Index("ix_token_usage_logs_provider", "provider"),
        Index("ix_token_usage_logs_model_name", "model_name"),
        Index("ix_token_usage_logs_latency_ms", "latency_ms"),
        Index("ix_token_usage_logs_cache_hit", "cache_hit"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    api_key_id: Mapped[UUID] = mapped_column(ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[TokenProvider] = mapped_column(
        SqlEnum(
            TokenProvider,
            name="token_provider_enum",
            native_enum=True,
            values_callable=_enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(18, 9), nullable=False, default=Decimal("0"))
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    endpoint: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class DailyAggregate(Base):
    __tablename__ = "daily_aggregates"
    __table_args__ = (
        UniqueConstraint("api_key_id", "date", name="uq_daily_aggregates_api_key_date"),
        Index("ix_daily_aggregates_date", "date"),
        Index("ix_daily_aggregates_api_key_id", "api_key_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    api_key_id: Mapped[UUID] = mapped_column(ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    total_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(18, 9), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class OptimizationRecommendation(Base):
    __tablename__ = "optimization_recommendations"
    __table_args__ = (
        Index("ix_optimization_recommendations_generated_at", "generated_at"),
        Index("ix_optimization_recommendations_is_dismissed", "is_dismissed"),
        Index("ix_optimization_recommendations_dedupe_key", "dedupe_key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    api_key_id: Mapped[UUID | None] = mapped_column(ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True, index=True)
    category: Mapped[RecommendationCategory] = mapped_column(
        SqlEnum(
            RecommendationCategory,
            name="recommendation_category_enum",
            native_enum=True,
            values_callable=_enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    severity: Mapped[RecommendationSeverity] = mapped_column(
        SqlEnum(
            RecommendationSeverity,
            name="recommendation_severity_enum",
            native_enum=True,
            values_callable=_enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    potential_saving_usd: Mapped[Decimal] = mapped_column(Numeric(18, 9), nullable=False, default=Decimal("0"))
    action_items_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    dedupe_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    is_dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BudgetAlert(Base):
    __tablename__ = "budget_alerts"
    __table_args__ = (
        Index("ix_budget_alerts_api_key_id", "api_key_id"),
        Index("ix_budget_alerts_cycle_start", "cycle_start"),
        Index("ix_budget_alerts_status", "status"),
        UniqueConstraint(
            "api_key_id",
            "cycle_start",
            "threshold_percent",
            name="uq_budget_alerts_api_key_cycle_threshold",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    api_key_id: Mapped[UUID] = mapped_column(ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    threshold_usd: Mapped[Decimal] = mapped_column(Numeric(18, 9), nullable=False)
    threshold_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_spend_usd: Mapped[Decimal] = mapped_column(Numeric(18, 9), nullable=False)
    budget_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 9), nullable=True)
    period: Mapped[str] = mapped_column(String(16), nullable=False, default="daily")
    cycle_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    cycle_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class APIKeyBudgetConfig(Base):
    __tablename__ = "api_key_budget_configs"
    __table_args__ = (
        UniqueConstraint("api_key_id", name="uq_api_key_budget_configs_api_key_id"),
        Index("ix_api_key_budget_configs_api_key_id", "api_key_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    api_key_id: Mapped[UUID] = mapped_column(ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    monthly_budget_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 9), nullable=True)
    alert_thresholds_json: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class BudgetChangeAuditLog(Base):
    __tablename__ = "budget_change_audit_logs"
    __table_args__ = (
        Index("ix_budget_change_audit_logs_api_key_id", "api_key_id"),
        Index("ix_budget_change_audit_logs_changed_by_user_id", "changed_by_user_id"),
        Index("ix_budget_change_audit_logs_changed_at", "changed_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    api_key_id: Mapped[UUID] = mapped_column(ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    changed_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    old_monthly_budget_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 9), nullable=True)
    new_monthly_budget_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 9), nullable=True)
    old_alert_thresholds_json: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    new_alert_thresholds_json: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
