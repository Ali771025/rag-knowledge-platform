"""Persona event contracts shared with async and audit layers."""

from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field

from app.internal.persona.enums import PersonaModifier, PersonaType


class PersonaEventEnvelope(BaseModel):
    """Base event envelope for persona-related events."""

    event_name: str = Field(..., min_length=1, max_length=128)
    session_id: str = Field(..., min_length=1, max_length=128)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PersonaAnalyzedEvent(PersonaEventEnvelope):
    """Placeholder event emitted when a persona analysis is produced."""

    event_name: str = "persona.analyzed"
    persona_type: PersonaType
    confidence: float = Field(..., ge=0.0, le=1.0)


class PersonaModifierAppliedEvent(PersonaEventEnvelope):
    """Placeholder event emitted when persona modifiers are applied."""

    event_name: str = "persona.modifier_applied"
    modifier: PersonaModifier
    threshold: float = Field(..., ge=0.0, le=1.0)
