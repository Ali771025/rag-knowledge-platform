"""SQLAlchemy repository implementations for conversion persistence contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.internal.conversion.enums import FunnelStage
from app.internal.conversion.repositories.interfaces import ConversionEventRepository, FunnelStateRepository
from app.models.persona_conversion import ConversionEvent, FunnelState


def _to_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


class SQLAlchemyFunnelStateRepository(FunnelStateRepository):
    """SQLAlchemy implementation for funnel state persistence."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_session_id(self, session_id: str) -> FunnelState | None:
        session_uuid = _to_uuid(session_id)
        stmt = select(FunnelState).where(FunnelState.session_id == session_uuid)
        return self.db.scalar(stmt)

    def upsert(self, payload: dict[str, object]) -> FunnelState:
        if "session_id" not in payload:
            raise ValueError("session_id is required for funnel state upsert")

        session_uuid = _to_uuid(payload["session_id"])
        existing = self.get_by_session_id(str(session_uuid))

        if existing is None:
            data = dict(payload)
            data["session_id"] = session_uuid
            state = FunnelState(**data)
            self.db.add(state)
            self.db.flush()
            self.db.refresh(state)
            return state

        mutable_fields = {"user_id", "stage", "stage_confidence", "cta_allowed", "state_payload"}
        for field, value in payload.items():
            if field in mutable_fields:
                setattr(existing, field, value)
        existing.updated_at = datetime.now(timezone.utc)
        self.db.add(existing)
        self.db.flush()
        self.db.refresh(existing)
        return existing

    def list_by_stage(self, stage: FunnelStage) -> list[FunnelState]:
        stmt = select(FunnelState).where(FunnelState.stage == stage).order_by(FunnelState.updated_at.desc())
        return list(self.db.scalars(stmt).all())


class SQLAlchemyConversionEventRepository(ConversionEventRepository):
    """SQLAlchemy implementation for conversion event persistence."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: dict[str, Any]) -> ConversionEvent:
        if "session_id" in payload:
            payload = dict(payload)
            payload["session_id"] = _to_uuid(payload["session_id"])
        if "funnel_state_id" in payload and payload["funnel_state_id"] is not None:
            payload = dict(payload)
            payload["funnel_state_id"] = _to_uuid(payload["funnel_state_id"])

        model = ConversionEvent(**payload)
        self.db.add(model)
        self.db.flush()
        self.db.refresh(model)
        return model

    def list_by_session_id(self, session_id: str) -> list[ConversionEvent]:
        session_uuid = _to_uuid(session_id)
        stmt = (
            select(ConversionEvent)
            .where(ConversionEvent.session_id == session_uuid)
            .order_by(ConversionEvent.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())
