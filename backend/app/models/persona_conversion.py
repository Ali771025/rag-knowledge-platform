"""ORM models for persona state and conversion funnel persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, Float, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.internal.conversion.enums import FunnelStage, TriggerType
from app.internal.persona.enums import PersonaModifier, PersonaType

PERSONA_TYPE_ENUM = SQLEnum(PersonaType, name="persona_type_enum")
PERSONA_MODIFIER_ENUM = SQLEnum(PersonaModifier, name="persona_modifier_enum")
FUNNEL_STAGE_ENUM = SQLEnum(FunnelStage, name="funnel_stage_enum")
TRIGGER_TYPE_ENUM = SQLEnum(TriggerType, name="trigger_type_enum")
JSONB_COMPAT = JSON().with_variant(JSONB, "postgresql")


class PersonaState(Base):
    """Current persona classification state for an active session."""

    __tablename__ = "persona_state"
    __table_args__ = (
        Index("ix_persona_state_session_updated", "session_id", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(nullable=False, unique=True, index=True)
    user_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    persona_type: Mapped[PersonaType] = mapped_column(PERSONA_TYPE_ENUM, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    active_modifiers: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    signals_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class PersonaHistory(Base):
    """Append-only history records for persona changes over time."""

    __tablename__ = "persona_history"
    __table_args__ = (
        Index("ix_persona_history_session_created", "session_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    persona_state_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    session_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    previous_persona_type: Mapped[PersonaType | None] = mapped_column(
        PERSONA_TYPE_ENUM,
        nullable=True,
    )
    new_persona_type: Mapped[PersonaType] = mapped_column(PERSONA_TYPE_ENUM, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


class ModifierHistory(Base):
    """Append-only history records for modifier application decisions."""

    __tablename__ = "modifier_history"
    __table_args__ = (
        Index("ix_modifier_history_session_created", "session_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    persona_state_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    session_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    modifier: Mapped[PersonaModifier] = mapped_column(PERSONA_MODIFIER_ENUM, nullable=False)
    is_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trigger_type: Mapped[TriggerType | None] = mapped_column(TRIGGER_TYPE_ENUM, nullable=True)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


class FunnelState(Base):
    """Current conversion funnel state for a session."""

    __tablename__ = "funnel_state"
    __table_args__ = (
        Index("ix_funnel_state_session_updated", "session_id", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(nullable=False, unique=True, index=True)
    user_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    stage: Mapped[FunnelStage] = mapped_column(FUNNEL_STAGE_ENUM, nullable=False)
    stage_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cta_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    state_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ConversionEvent(Base):
    """Append-only conversion events emitted by the funnel evaluator."""

    __tablename__ = "conversion_events"
    __table_args__ = (
        Index("ix_conversion_events_persona", "persona"),
        Index("ix_conversion_events_stage", "stage"),
        Index("ix_conversion_events_outcome", "outcome"),
        Index("ix_conversion_events_session_created", "session_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    session_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    funnel_state_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    event_type: Mapped[TriggerType] = mapped_column(
        TRIGGER_TYPE_ENUM,
        nullable=False,
        default=TriggerType.EDUCATIONAL_NUDGE,
    )
    stage: Mapped[FunnelStage] = mapped_column(FUNNEL_STAGE_ENUM, nullable=False)
    persona_type: Mapped[PersonaType | None] = mapped_column(
        PERSONA_TYPE_ENUM,
        nullable=True,
    )
    persona: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    engagement_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    triggers_used: Mapped[list[str]] = mapped_column(JSONB_COMPAT, nullable=False, default=list)
    cta_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cta_strength: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    outcome: Mapped[str] = mapped_column(String(64), nullable=False, default="no_change")
    cta_outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    experiment_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    experiment_variant: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


class TriggerEffectiveness(Base):
    """Materialized trigger-level success metrics for lightweight analytics reads."""

    __tablename__ = "trigger_effectiveness"
    __table_args__ = (
        Index("ix_trigger_effectiveness_persona", "persona"),
        Index("ix_trigger_effectiveness_stage", "stage"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    trigger_primary: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    trigger_secondary: Mapped[str | None] = mapped_column(String(64), nullable=True)
    persona: Mapped[str] = mapped_column(String(64), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
