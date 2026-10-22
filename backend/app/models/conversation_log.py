"""Conversation-level observability log ORM model."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConversationLog(Base):
    """Stores request-level and conversation-level observability records."""

    __tablename__ = "conversation_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    session_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    conversation_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="recorded", index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="request", index=True)
    operation_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 9), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
