"""SQLAlchemy persistence models for cache usage logging."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SemanticCacheLog(Base):
    """Persistence model for semantic/RAG/session cache access and invalidation events."""

    __tablename__ = "semantic_cache_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    cache_type: Mapped[str] = mapped_column(String(32), nullable=False, default="semantic", index=True)
    namespace: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    cache_key: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    cache_hit: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    similarity_score: Mapped[float | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    invalidated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_saved_usd: Mapped[float | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


# Compatibility aliases for earlier service-layer references.
CacheAccessLog = SemanticCacheLog
CacheInvalidationLog = SemanticCacheLog
