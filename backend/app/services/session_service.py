from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.redis_client import get_session_state, set_session_state
from app.models.session import Session
from app.repositories.session_repository import SessionRepository


class SessionService:
    def __init__(self, session_repository: SessionRepository) -> None:
        self.session_repository = session_repository

    def create_session(
        self,
        *,
        user_id: UUID,
        title: str | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> Session:
        state = initial_state or {}
        session = self.session_repository.create(user_id=user_id, title=title, state=state)
        set_session_state(str(session.id), session.state)
        return session

    def get_session(self, session_id: UUID) -> Session | None:
        return self.session_repository.get_by_id(session_id)

    def get_session_state(self, session_id: UUID) -> dict[str, Any] | None:
        cached_state = get_session_state(str(session_id))
        if cached_state is not None:
            return cached_state

        session = self.session_repository.get_by_id(session_id)
        if session is None:
            return None

        db_state = session.state or {}
        set_session_state(str(session.id), db_state)
        return db_state

    def update_session_state(self, session_id: UUID, state: dict[str, Any]) -> dict[str, Any] | None:
        session = self.session_repository.get_by_id(session_id)
        if session is None:
            return None

        updated = self.session_repository.update_state(session, state)
        set_session_state(str(updated.id), updated.state)
        return updated.state
