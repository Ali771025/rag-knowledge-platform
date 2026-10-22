"""SQLAlchemy repositories for analytics persistence."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.persona_conversion import ConversionEvent, TriggerEffectiveness


def _to_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


class ConversionAnalyticsRepository:
    """Persistence adapter for conversion outcome analytics events."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: dict[str, Any]) -> ConversionEvent:
        data = dict(payload)
        if "session_id" in data:
            data["session_id"] = _to_uuid(data["session_id"])
        if "user_id" in data and data["user_id"] is not None:
            data["user_id"] = _to_uuid(data["user_id"])
        if "funnel_state_id" in data and data["funnel_state_id"] is not None:
            data["funnel_state_id"] = _to_uuid(data["funnel_state_id"])

        model = ConversionEvent(**data)
        self.db.add(model)
        self.db.flush()
        self.db.refresh(model)
        return model

    def list_by_session_id(self, session_id: UUID | str, limit: int = 100) -> list[ConversionEvent]:
        stmt = (
            select(ConversionEvent)
            .where(ConversionEvent.session_id == _to_uuid(session_id))
            .order_by(desc(ConversionEvent.created_at))
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def conversion_rate_by_persona(self) -> dict[str, float]:
        total_stmt = select(
            ConversionEvent.persona,
            func.count(ConversionEvent.id),
        ).group_by(ConversionEvent.persona)
        success_stmt = (
            select(
                ConversionEvent.persona,
                func.count(ConversionEvent.id),
            )
            .where(ConversionEvent.outcome.in_(("economic_action_ready", "stage_advanced")))
            .group_by(ConversionEvent.persona)
        )
        totals = {persona: int(count) for persona, count in self.db.execute(total_stmt).all() if persona}
        successes = {persona: int(count) for persona, count in self.db.execute(success_stmt).all() if persona}

        rates: dict[str, float] = {}
        for persona, total in totals.items():
            if total <= 0:
                continue
            rates[persona] = successes.get(persona, 0) / total
        return rates

    def funnel_dropout_by_stage(self) -> dict[str, int]:
        stmt = (
            select(
                ConversionEvent.stage,
                func.count(ConversionEvent.id),
            )
            .where(ConversionEvent.outcome == "stage_held")
            .group_by(ConversionEvent.stage)
        )
        return {stage.value if hasattr(stage, "value") else str(stage): int(count) for stage, count in self.db.execute(stmt).all()}


class TriggerEffectivenessRepository:
    """Persistence adapter for trigger effectiveness snapshots."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: dict[str, Any]) -> TriggerEffectiveness:
        model = TriggerEffectiveness(**payload)
        self.db.add(model)
        self.db.flush()
        self.db.refresh(model)
        return model

    def upsert_by_signature(self, payload: dict[str, Any]) -> TriggerEffectiveness:
        stmt = select(TriggerEffectiveness).where(
            TriggerEffectiveness.trigger_primary == payload["trigger_primary"],
            TriggerEffectiveness.trigger_secondary == payload.get("trigger_secondary"),
            TriggerEffectiveness.persona == payload["persona"],
            TriggerEffectiveness.stage == payload["stage"],
        )
        existing = self.db.scalar(stmt)
        if existing is None:
            return self.create(payload)

        existing.success_rate = float(payload["success_rate"])
        existing.sample_size = int(payload["sample_size"])
        self.db.add(existing)
        self.db.flush()
        self.db.refresh(existing)
        return existing

    def trigger_performance_by_stage(self, stage: str) -> list[TriggerEffectiveness]:
        stmt = (
            select(TriggerEffectiveness)
            .where(TriggerEffectiveness.stage == stage)
            .order_by(desc(TriggerEffectiveness.success_rate), desc(TriggerEffectiveness.sample_size))
        )
        return list(self.db.scalars(stmt).all())
