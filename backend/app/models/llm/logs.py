"""SQLAlchemy persistence models for LLM usage and routing decision logs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LLMUsageLog(Base):
    """Persistence model for provider usage/cost/latency records."""

    __tablename__ = "llm_usage_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(nullable=False, default=0.0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cache_saved_cost_usd: Mapped[float] = mapped_column(nullable=False, default=0.0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


class RoutingDecisionLog(Base):
    """Persistence model for routing outcomes and fallback planning visibility."""

    __tablename__ = "routing_decisions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    complexity_label: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    complexity_score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    fallback_provider: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    fallback_model: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(nullable=True)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


# Compatibility aliases for earlier service-layer references.
LLMRequestLog = RoutingDecisionLog
LLMResponseLog = LLMUsageLog
