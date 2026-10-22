"""Pydantic contracts for conversion funnel orchestration I/O."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.internal.conversion.policy_enums import CTAAction, JourneyStage, PsychologicalTrigger


class ConversionFunnelRequest(BaseModel):
    """Input payload for conversion funnel service updates."""

    session_id: str = Field(..., min_length=1, max_length=128)
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    persona_label: str = Field(..., min_length=1, max_length=64)
    persona_confidence: float = Field(..., ge=0.0, le=1.0)
    trust_score: float = Field(..., ge=0.0, le=1.0)
    current_stage: JourneyStage = JourneyStage.ENTRY
    intent: str = Field(default="", max_length=256)
    is_ambiguous: bool = False
    repeated_interaction_count: int = Field(default=0, ge=0)
    clarification_success_count: int = Field(default=0, ge=0)
    objection_count: int = Field(default=0, ge=0)
    confusion_count: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConversionFunnelResponse(BaseModel):
    """Output payload with trust/stage/trigger/cta orchestration metadata."""

    session_id: str
    previous_trust_score: float = Field(..., ge=0.0, le=1.0)
    updated_trust_score: float = Field(..., ge=0.0, le=1.0)
    previous_stage: JourneyStage
    next_stage: JourneyStage
    stage_transition_allowed: bool
    primary_trigger: PsychologicalTrigger
    secondary_trigger: PsychologicalTrigger | None = None
    allowed_actions: list[CTAAction] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    orchestration_metadata: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")
