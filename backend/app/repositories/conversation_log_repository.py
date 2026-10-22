from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.conversation_log import ConversationLog
from app.observability.repository_models import LatencySummaryInputs


class ConversationLogRepository:
    """Data-access helpers for `conversation_logs` records and aggregates."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **fields: Any) -> ConversationLog:
        log = ConversationLog(**fields)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def count_requests_today(self, *, now: datetime | None = None) -> int:
        anchor = (now or datetime.now(UTC)).astimezone(UTC)
        day_start = datetime(anchor.year, anchor.month, anchor.day, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)

        stmt = select(func.count(ConversationLog.id)).where(
            ConversationLog.created_at >= day_start,
            ConversationLog.created_at < day_end,
        )
        return int(self.db.scalar(stmt) or 0)

    def average_latency_summary_inputs(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        state: str | None = None,
        endpoint: str | None = None,
    ) -> LatencySummaryInputs:
        stmt = select(
            func.count(ConversationLog.id),
            func.coalesce(func.sum(ConversationLog.latency_ms), 0.0),
            func.coalesce(func.avg(ConversationLog.latency_ms), 0.0),
            func.coalesce(func.min(ConversationLog.latency_ms), 0.0),
            func.coalesce(func.max(ConversationLog.latency_ms), 0.0),
        ).where(ConversationLog.latency_ms.is_not(None))

        if start_at is not None:
            stmt = stmt.where(ConversationLog.created_at >= start_at)
        if end_at is not None:
            stmt = stmt.where(ConversationLog.created_at < end_at)
        if state is not None:
            stmt = stmt.where(ConversationLog.state == state)
        if endpoint is not None:
            stmt = stmt.where(ConversationLog.operation_name == endpoint)

        row = self.db.execute(stmt).one()
        sample_count = int(row[0] or 0)
        return LatencySummaryInputs(
            sample_count=sample_count,
            total_latency_ms=float(row[1] or 0.0),
            average_latency_ms=float(row[2] or 0.0),
            min_latency_ms=float(row[3] or 0.0),
            max_latency_ms=float(row[4] or 0.0),
        )

    def list_latency_values(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        state: str | None = None,
        endpoint: str | None = None,
    ) -> list[float]:
        stmt = select(ConversationLog.latency_ms).where(ConversationLog.latency_ms.is_not(None))

        if start_at is not None:
            stmt = stmt.where(ConversationLog.created_at >= start_at)
        if end_at is not None:
            stmt = stmt.where(ConversationLog.created_at < end_at)
        if state is not None:
            stmt = stmt.where(ConversationLog.state == state)
        if endpoint is not None:
            stmt = stmt.where(ConversationLog.operation_name == endpoint)

        stmt = stmt.order_by(ConversationLog.latency_ms.asc())
        return [float(value) for value in self.db.scalars(stmt).all() if value is not None]

    def aggregate_state_distribution(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> dict[str, int]:
        stmt = select(ConversationLog.state, func.count(ConversationLog.id)).group_by(ConversationLog.state)

        if start_at is not None:
            stmt = stmt.where(ConversationLog.created_at >= start_at)
        if end_at is not None:
            stmt = stmt.where(ConversationLog.created_at < end_at)

        rows = self.db.execute(stmt).all()
        return {str(row[0]): int(row[1] or 0) for row in rows}
