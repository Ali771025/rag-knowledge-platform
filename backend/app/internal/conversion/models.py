"""Internal conversion domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from app.internal.conversion.enums import FunnelStage, TriggerType as LegacyTriggerType
from app.internal.conversion.policy_enums import (
    CTAOutcome,
    ConversionActionType,
    ConversionOutcome,
    EconomicSuggestionStrength,
    JourneyStage as PolicyFunnelStage,
    TriggerType as PolicyTriggerType,
)
from app.internal.persona.enums import PersonaModifier


@dataclass(frozen=True, slots=True)
class ConversionEvaluationResult:
    """Result object exchanged across internal conversion components."""

    session_id: str
    previous_stage: FunnelStage
    next_stage: FunnelStage
    confidence: float
    selected_trigger: LegacyTriggerType | None = None
    cta_allowed: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConversionDecisionInput(BaseModel):
    """Shared contract consumed by CTA/conversion policy decisions."""

    persona: str = Field(..., min_length=1, max_length=64)
    confidence: float = Field(..., ge=0.0, le=1.0)
    stage: PolicyFunnelStage
    trust_score: float = Field(..., ge=0.0, le=1.0)
    intent: str = Field(default="", max_length=256)
    modifiers: list[PersonaModifier] = Field(default_factory=list)
    selected_triggers: list[PolicyTriggerType] = Field(default_factory=list, max_length=2)
    is_ambiguous: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConversionDecisionOutput(BaseModel):
    """Shared typed output contract for conversion/CTA decision outcomes."""

    outcome: ConversionOutcome
    cta_outcome: CTAOutcome
    allowed_actions: list[ConversionActionType] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    economic_suggestion_strength: EconomicSuggestionStrength = EconomicSuggestionStrength.NONE
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")
