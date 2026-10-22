"""Conversion event contracts shared with async and audit layers."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from app.internal.conversion.enums import FunnelStage, TriggerType
from app.internal.conversion.policy_enums import EconomicSuggestionStrength, JourneyStage
from app.internal.conversion.rule_engine import ConversionDecisionAllowedAction


class ConversionEventEnvelope(BaseModel):
    """Base event envelope for conversion-related events."""

    event_name: str = Field(..., min_length=1, max_length=128)
    session_id: str = Field(..., min_length=1, max_length=128)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConversionEvaluatedEvent(ConversionEventEnvelope):
    """Placeholder event emitted when conversion evaluation is produced."""

    event_name: str = "conversion.evaluated"
    next_stage: FunnelStage
    confidence: float = Field(..., ge=0.0, le=1.0)


class TriggerSelectedEvent(ConversionEventEnvelope):
    """Placeholder event emitted when a conversion trigger is selected."""

    event_name: str = "conversion.trigger_selected"
    trigger_type: TriggerType
    stage: FunnelStage


class ConversionDecisionEvaluatedEvent(ConversionEventEnvelope):
    """Event emitted when conversion decision rule engine evaluation completes."""

    event_name: str = "conversion.decision_evaluated"
    persona: str = Field(..., min_length=1, max_length=64)
    confidence: float = Field(..., ge=0.0, le=1.0)
    intent: str = Field(..., min_length=1, max_length=64)
    stage: JourneyStage
    trust_score: float = Field(..., ge=0.0, le=1.0)
    engagement_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rejection_count: int = Field(default=0, ge=0)
    allowed_actions: list[ConversionDecisionAllowedAction] = Field(default_factory=list)
    economic_suggestion_strength: EconomicSuggestionStrength = EconomicSuggestionStrength.NONE
    cta_allowed: bool = False
    block_reason: str | None = Field(default=None, min_length=1, max_length=255)
    matched_rules: list[str] = Field(default_factory=list)
