from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.session_log import SessionLog
from app.observability.enums import SessionState


class SessionLogRepository:
    """Data-access helpers for `session_logs` records and lifecycle aggregates."""

    _ACTIVE_STATES = {
        SessionState.STARTED.value,
        SessionState.ACTIVE.value,
        SessionState.IDLE.value,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **fields: Any) -> SessionLog:
        log = SessionLog(**fields)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def count_active_sessions(self, *, now: datetime | None = None) -> int:
        anchor = (now or datetime.now(UTC)).astimezone(UTC)

        subquery = (
            select(
                SessionLog.session_id.label("session_id"),
                func.max(SessionLog.created_at).label("latest_created_at"),
            )
            .group_by(SessionLog.session_id)
            .subquery()
        )

        stmt = (
            select(func.count(SessionLog.id))
            .join(
                subquery,
                and_(
                    SessionLog.session_id == subquery.c.session_id,
                    SessionLog.created_at == subquery.c.latest_created_at,
                ),
            )
            .where(
                SessionLog.state.in_(self._ACTIVE_STATES),
                SessionLog.started_at <= anchor,
                or_(SessionLog.ended_at.is_(None), SessionLog.ended_at > anchor),
            )
        )

        return int(self.db.scalar(stmt) or 0)
