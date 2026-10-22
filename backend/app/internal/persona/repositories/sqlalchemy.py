"""SQLAlchemy repository implementations for persona persistence contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.internal.persona.enums import PersonaModifier
from app.internal.persona.repositories.interfaces import (
    ModifierHistoryRepository,
    PersonaHistoryRepository,
    PersonaStateRepository,
)
from app.models.persona_conversion import ModifierHistory, PersonaHistory, PersonaState


def _to_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


class SQLAlchemyPersonaStateRepository(PersonaStateRepository):
    """SQLAlchemy implementation for persona state persistence."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_session_id(self, session_id: str) -> PersonaState | None:
        session_uuid = _to_uuid(session_id)
        stmt = select(PersonaState).where(PersonaState.session_id == session_uuid)
        return self.db.scalar(stmt)

    def upsert(self, payload: dict[str, object]) -> PersonaState:
        if "session_id" not in payload:
            raise ValueError("session_id is required for persona state upsert")

        session_uuid = _to_uuid(payload["session_id"])
        existing = self.get_by_session_id(str(session_uuid))

        if existing is None:
            data = dict(payload)
            data["session_id"] = session_uuid
            state = PersonaState(**data)
            self.db.add(state)
            self.db.flush()
            self.db.refresh(state)
            return state

        mutable_fields = {
            "user_id",
            "persona_type",
            "confidence",
            "active_modifiers",
            "signals_json",
        }
        for field, value in payload.items():
            if field in mutable_fields:
                setattr(existing, field, value)
        existing.updated_at = datetime.now(timezone.utc)
        self.db.add(existing)
        self.db.flush()
        self.db.refresh(existing)
        return existing


class SQLAlchemyPersonaHistoryRepository(PersonaHistoryRepository):
    """SQLAlchemy implementation for persona history persistence."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: dict[str, Any]) -> PersonaHistory:
        if "session_id" in payload:
            payload = dict(payload)
            payload["session_id"] = _to_uuid(payload["session_id"])
        if "persona_state_id" in payload:
            payload = dict(payload)
            payload["persona_state_id"] = _to_uuid(payload["persona_state_id"])

        model = PersonaHistory(**payload)
        self.db.add(model)
        self.db.flush()
        self.db.refresh(model)
        return model


class SQLAlchemyModifierHistoryRepository(ModifierHistoryRepository):
    """SQLAlchemy implementation for modifier history persistence."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_session_id(self, session_id: str) -> list[ModifierHistory]:
        session_uuid = _to_uuid(session_id)
        stmt = (
            select(ModifierHistory)
            .where(ModifierHistory.session_id == session_uuid)
            .order_by(ModifierHistory.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def create(self, payload: dict[str, Any]) -> ModifierHistory:
        if "session_id" in payload:
            payload = dict(payload)
            payload["session_id"] = _to_uuid(payload["session_id"])
        if "persona_state_id" in payload:
            payload = dict(payload)
            payload["persona_state_id"] = _to_uuid(payload["persona_state_id"])

        model = ModifierHistory(**payload)
        self.db.add(model)
        self.db.flush()
        self.db.refresh(model)
        return model

    def list_by_modifier(self, modifier: PersonaModifier) -> list[ModifierHistory]:
        stmt = (
            select(ModifierHistory)
            .where(ModifierHistory.modifier == modifier)
            .order_by(ModifierHistory.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())
