"""Typed models for Redis-backed persona transition buffering."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.internal.persona.enums import PersonaType


class PersonaTransitionEvaluation(BaseModel):
    """Compact snapshot of one persona evaluation result for short-lived buffering."""

    persona_type: PersonaType
    confidence: float = Field(..., ge=0.0, le=1.0)
    persona_scores: dict[PersonaType, float] = Field(default_factory=dict)
    signal_summary: dict[str, float] = Field(default_factory=dict)
    source: str = Field(default="persona_engine", min_length=1, max_length=64)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_signal_summary(self) -> "PersonaTransitionEvaluation":
        for persona, score in self.persona_scores.items():
            _ = persona
            if score < 0.0:
                raise ValueError("persona_scores values must be >= 0.0")
        if len(self.signal_summary) > 12:
            raise ValueError("signal_summary must contain at most 12 entries")
        for key, value in self.signal_summary.items():
            if not key.strip():
                raise ValueError("signal_summary keys must be non-empty")
            if len(key) > 64:
                raise ValueError("signal_summary keys must be <= 64 characters")
            if value < 0.0 or value > 1.0:
                raise ValueError("signal_summary values must be between 0.0 and 1.0")
        return self


class TransitionCandidate(BaseModel):
    """Potential persona transition candidate tracked between evaluations."""

    candidate_persona: PersonaType
    support: float = Field(..., ge=0.0, le=1.0)
    reason: str | None = Field(default=None, min_length=1, max_length=200)
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PersonaTransitionBuffer(BaseModel):
    """Ephemeral session-scoped buffer for transition-supporting evaluation data."""

    session_id: str = Field(..., min_length=1, max_length=128)
    evaluations: list[PersonaTransitionEvaluation] = Field(default_factory=list)
    rolling_confidence: list[float] = Field(default_factory=list)
    transition_candidate: TransitionCandidate | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_lengths(self) -> "PersonaTransitionBuffer":
        if len(self.evaluations) > 3:
            raise ValueError("evaluations must contain at most 3 items")
        if len(self.rolling_confidence) > 3:
            raise ValueError("rolling_confidence must contain at most 3 items")
        for value in self.rolling_confidence:
            if value < 0.0 or value > 1.0:
                raise ValueError("rolling_confidence values must be between 0.0 and 1.0")
        return self
