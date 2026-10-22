"""Cost observability log ORM model."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CostLog(Base):
    """Stores token usage and monetary usage records."""

    __tablename__ = "cost_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    session_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="recorded", index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_cost: Mapped[Decimal] = mapped_column(Numeric(18, 9), nullable=False, default=Decimal("0"))
    completion_cost: Mapped[Decimal] = mapped_column(Numeric(18, 9), nullable=False, default=Decimal("0"))
    cache_cost: Mapped[Decimal] = mapped_column(Numeric(18, 9), nullable=False, default=Decimal("0"))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 9), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
