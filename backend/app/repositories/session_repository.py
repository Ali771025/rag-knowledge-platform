from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.session import Session as UserSession


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, user_id: UUID, title: str | None = None, state: dict[str, Any] | None = None) -> UserSession:
        session = UserSession(user_id=user_id, title=title, state=state or {})
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_id(self, session_id: UUID) -> UserSession | None:
        return self.db.get(UserSession, session_id)

    def update_state(self, session: UserSession, state: dict[str, Any]) -> UserSession:
        session.state = state
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
