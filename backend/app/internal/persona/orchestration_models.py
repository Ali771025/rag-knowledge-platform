"""Pydantic contracts for persona intelligence orchestration I/O."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.internal.persona.enums import PersonaModifier, PersonaType


class PersonaIntelligenceRequest(BaseModel):
    """Input payload for persona intelligence service orchestration."""

    session_id: str = Field(..., min_length=1, max_length=128)
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=8000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    recent_messages: list[str] = Field(default_factory=list)
    current_persona: PersonaType | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PersonaTransitionSummary(BaseModel):
    """Transition decision summary suitable for dialogue-level consumers."""

    candidate_persona: PersonaType
    recommendation_allowed: bool
    transition_allowed: bool
    score_ratio: float
    stable_evidence_count: int
    reasons: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class PersonaIntelligenceResponse(BaseModel):
    """Output payload from persona intelligence orchestration pipeline."""

    session_id: str
    assigned_persona: PersonaType
    assignment_label: str
    is_low_confidence: bool
    confidence_gap: float
    confidence_threshold: float
    persona_scores: dict[PersonaType, float] = Field(default_factory=dict)
    modifiers: list[PersonaModifier] = Field(default_factory=list)
    transition: PersonaTransitionSummary
    dialogue_hints: dict[str, Any] = Field(default_factory=dict)
    orchestration_metadata: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")
