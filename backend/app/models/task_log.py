"""Task execution log ORM model."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

TaskLogStatus = Literal["pending", "started", "retrying", "succeeded", "failed"]


class TaskLog(Base):
    """Tracks queue task lifecycle information for auditing and debugging."""

    __tablename__ = "task_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    queue_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[TaskLogStatus] = mapped_column(String(32), nullable=False, default="pending", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
