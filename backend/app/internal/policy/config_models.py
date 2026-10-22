"""Typed policy configuration models for persona and conversion components."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.internal.conversion.enums import FunnelStage, TriggerType
from app.internal.persona.enums import PersonaModifier, PersonaType
from app.internal.persona.signal_models import PersonaSignal


class PersonaSignalExtractionConfig(BaseModel):
    """Configuration for deterministic persona signal extraction rules."""

    hesitation_terms: tuple[str, ...] = (
        "maybe",
        "not sure",
        "i think",
        "perhaps",
        "unsure",
    )
    proof_terms: tuple[str, ...] = (
        "case study",
        "evidence",
        "proof",
        "benchmark",
        "example",
    )
    roi_terms: tuple[str, ...] = (
        "roi",
        "cost",
        "budget",
        "savings",
        "value",
    )
    analytical_terms: tuple[str, ...] = (
        "compare",
        "tradeoff",
        "analysis",
        "metric",
        "breakdown",
    )
    urgency_terms: tuple[str, ...] = (
        "asap",
        "today",
        "urgent",
        "deadline",
        "quickly",
    )
    gamification_terms: tuple[str, ...] = (
        "streak",
        "badge",
        "points",
        "level",
        "reward",
    )
    lexical_terms: tuple[str, ...] = (
        "help",
        "guide",
        "need",
        "want",
        "looking",
    )
    keyword_cap: int = Field(default=3, ge=1, le=10)
    metadata_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "follow_up_count": 0.5,
            "messages_in_session": 0.3,
            "returning_user": 0.1,
            "intent_events": 0.1,
        }
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_metadata_weights(self) -> "PersonaSignalExtractionConfig":
        for key, value in self.metadata_weights.items():
            if not key.strip():
                raise ValueError("metadata_weights keys must be non-empty")
            if value < 0.0:
                raise ValueError("metadata_weights values must be >= 0.0")
        return self


class PersonaScoringConfig(BaseModel):
    """Configuration for weighted persona scoring from extracted signals."""

    decay_factor_base: float = Field(default=0.9, ge=0.0, le=1.0)
    confidence_neutral_threshold: float = Field(default=0.18, ge=0.0, le=1.0)
    signal_weights: dict[PersonaType, dict[PersonaSignal, float]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_signal_weights(self) -> "PersonaScoringConfig":
        for persona, weights in self.signal_weights.items():
            _ = persona
            for signal, value in weights.items():
                _ = signal
                if value < -5.0 or value > 5.0:
                    raise ValueError("signal weight must be between -5.0 and 5.0")
        return self


class ModifierRuleConfig(BaseModel):
    """Rule weights, keyword sets, and thresholding for one persona modifier."""

    keywords: tuple[str, ...] = ()
    metadata_flags: tuple[str, ...] = ()
    keyword_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    metadata_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    threshold: float = Field(default=0.35, ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")


class PersonaModifierDetectionConfig(BaseModel):
    """Configuration for rule-based persona modifier detection."""

    rules: dict[PersonaModifier, ModifierRuleConfig] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class PersonaTransitionConfig(BaseModel):
    """Configuration for deterministic persona transition decisioning."""

    min_score_multiplier: float = Field(default=1.25, ge=1.0, le=10.0)
    stability_window: int = Field(default=3, ge=2, le=10)
    trust_low_speed_penalty: float = Field(default=0.5, ge=0.0, le=0.9)

    model_config = ConfigDict(extra="forbid")


class PersonaPolicyConfig(BaseModel):
    """Policy settings that govern persona extraction, scoring, and confidence."""

    confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    persona_weights: dict[PersonaType, float] = Field(default_factory=dict)
    modifier_thresholds: dict[PersonaModifier, float] = Field(default_factory=dict)
    signal_extraction: PersonaSignalExtractionConfig = Field(default_factory=PersonaSignalExtractionConfig)
    scoring: PersonaScoringConfig = Field(default_factory=PersonaScoringConfig)
    modifier_detection: PersonaModifierDetectionConfig = Field(default_factory=PersonaModifierDetectionConfig)
    transition: PersonaTransitionConfig = Field(default_factory=PersonaTransitionConfig)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_weights(self) -> "PersonaPolicyConfig":
        for persona, value in self.persona_weights.items():
            _ = persona
            if value < 0.0:
                raise ValueError("persona_weights values must be >= 0.0")

        for modifier, value in self.modifier_thresholds.items():
            _ = modifier
            if value < 0.0 or value > 1.0:
                raise ValueError("modifier_thresholds values must be between 0.0 and 1.0")

        return self


class TriggerPolicyConfig(BaseModel):
    """Policy settings for selecting trigger strategies by funnel stage."""

    stage_trigger_map: dict[FunnelStage, list[TriggerType]] = Field(default_factory=dict)
    fallback_trigger: TriggerType = TriggerType.EDUCATIONAL_NUDGE

    model_config = ConfigDict(extra="forbid")


class CTAGatingPolicyConfig(BaseModel):
    """Policy settings that gate CTA visibility and permissions."""

    min_stage_for_cta: FunnelStage = FunnelStage.DECISION
    require_high_intent_modifier: bool = False

    model_config = ConfigDict(extra="forbid")


class TrustDeltaConfig(BaseModel):
    """Configurable trust score deltas applied during funnel interactions."""

    repeated_interaction: float = Field(default=0.03, ge=-1.0, le=1.0)
    clarification_success: float = Field(default=0.05, ge=-1.0, le=1.0)
    objection: float = Field(default=-0.04, ge=-1.0, le=1.0)
    confusion: float = Field(default=-0.06, ge=-1.0, le=1.0)

    model_config = ConfigDict(extra="forbid")


class TrustPolicyConfig(BaseModel):
    """Policy configuration for deterministic trust score updates."""

    deltas: TrustDeltaConfig = Field(default_factory=TrustDeltaConfig)

    model_config = ConfigDict(extra="forbid")


class ConversionPolicyConfig(BaseModel):
    """Policy settings that govern conversion stage transitions and trigger selection."""

    transition_thresholds: dict[FunnelStage, float] = Field(default_factory=dict)
    trigger_policy: TriggerPolicyConfig = Field(default_factory=TriggerPolicyConfig)
    cta_policy: CTAGatingPolicyConfig = Field(default_factory=CTAGatingPolicyConfig)
    trust: TrustPolicyConfig = Field(default_factory=TrustPolicyConfig)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_thresholds(self) -> "ConversionPolicyConfig":
        for stage, value in self.transition_thresholds.items():
            _ = stage
            if value < 0.0 or value > 1.0:
                raise ValueError("transition_thresholds values must be between 0.0 and 1.0")
        return self


class PersonaConversionPolicyConfig(BaseModel):
    """Root config model for persona and conversion policy data."""

    version: str = Field(default="1.0", min_length=1, max_length=32)
    persona: PersonaPolicyConfig = Field(default_factory=PersonaPolicyConfig)
    conversion: ConversionPolicyConfig = Field(default_factory=ConversionPolicyConfig)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def inject_defaults(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        persona = value.setdefault("persona", {})
        conversion = value.setdefault("conversion", {})
        trigger_policy = conversion.setdefault("trigger_policy", {})
        signal_extraction = persona.setdefault("signal_extraction", {})
        scoring = persona.setdefault("scoring", {})
        modifier_detection = persona.setdefault("modifier_detection", {})
        transition = persona.setdefault("transition", {})

        persona.setdefault(
            "persona_weights",
            {
                PersonaType.EXPLORER.value: 1.0,
                PersonaType.ANALYST.value: 1.0,
                PersonaType.PRAGMATIST.value: 1.0,
                PersonaType.EXECUTOR.value: 1.0,
            },
        )
        persona.setdefault(
            "modifier_thresholds",
            {
                PersonaModifier.HIGH_INTENT.value: 0.7,
                PersonaModifier.BUDGET_SENSITIVE.value: 0.55,
                PersonaModifier.RISK_AVERSE.value: 0.6,
                PersonaModifier.TIME_CONSTRAINED.value: 0.65,
                PersonaModifier.TRUST_LOW.value: 0.45,
                PersonaModifier.AUTHORITY_DRIVEN.value: 0.4,
                PersonaModifier.COMMUNITY_DRIVEN.value: 0.4,
                PersonaModifier.INDIVIDUAL_DRIVEN.value: 0.4,
                PersonaModifier.REGULATION_SENSITIVE.value: 0.4,
            },
        )
        signal_extraction.setdefault(
            "metadata_weights",
            {
                "follow_up_count": 0.5,
                "messages_in_session": 0.3,
                "returning_user": 0.1,
                "intent_events": 0.1,
            },
        )
        scoring.setdefault("decay_factor_base", 0.9)
        scoring.setdefault("confidence_neutral_threshold", 0.18)
        scoring.setdefault(
            "signal_weights",
            {
                PersonaType.EXPLORER.value: {
                    PersonaSignal.LEXICAL_ENGAGEMENT.value: 0.65,
                    PersonaSignal.HESITATION.value: 0.15,
                    PersonaSignal.PROOF_SEEKING.value: 0.35,
                    PersonaSignal.ROI_SEEKING.value: 0.4,
                    PersonaSignal.ANALYTICAL_DEPTH.value: 0.45,
                    PersonaSignal.URGENCY.value: 0.5,
                    PersonaSignal.GAMIFICATION_AFFINITY.value: 0.9,
                    PersonaSignal.ENGAGEMENT_PERSISTENCE.value: 0.75,
                    PersonaSignal.METADATA_BEHAVIORAL.value: 0.6,
                },
                PersonaType.ANALYST.value: {
                    PersonaSignal.LEXICAL_ENGAGEMENT.value: 0.45,
                    PersonaSignal.HESITATION.value: 0.2,
                    PersonaSignal.PROOF_SEEKING.value: 0.95,
                    PersonaSignal.ROI_SEEKING.value: 0.75,
                    PersonaSignal.ANALYTICAL_DEPTH.value: 1.0,
                    PersonaSignal.URGENCY.value: 0.35,
                    PersonaSignal.GAMIFICATION_AFFINITY.value: 0.2,
                    PersonaSignal.ENGAGEMENT_PERSISTENCE.value: 0.55,
                    PersonaSignal.METADATA_BEHAVIORAL.value: 0.4,
                },
                PersonaType.PRAGMATIST.value: {
                    PersonaSignal.LEXICAL_ENGAGEMENT.value: 0.55,
                    PersonaSignal.HESITATION.value: 0.1,
                    PersonaSignal.PROOF_SEEKING.value: 0.5,
                    PersonaSignal.ROI_SEEKING.value: 1.0,
                    PersonaSignal.ANALYTICAL_DEPTH.value: 0.6,
                    PersonaSignal.URGENCY.value: 0.7,
                    PersonaSignal.GAMIFICATION_AFFINITY.value: 0.25,
                    PersonaSignal.ENGAGEMENT_PERSISTENCE.value: 0.6,
                    PersonaSignal.METADATA_BEHAVIORAL.value: 0.7,
                },
                PersonaType.EXECUTOR.value: {
                    PersonaSignal.LEXICAL_ENGAGEMENT.value: 0.5,
                    PersonaSignal.HESITATION.value: -0.2,
                    PersonaSignal.PROOF_SEEKING.value: 0.4,
                    PersonaSignal.ROI_SEEKING.value: 0.65,
                    PersonaSignal.ANALYTICAL_DEPTH.value: 0.4,
                    PersonaSignal.URGENCY.value: 1.0,
                    PersonaSignal.GAMIFICATION_AFFINITY.value: 0.45,
                    PersonaSignal.ENGAGEMENT_PERSISTENCE.value: 0.7,
                    PersonaSignal.METADATA_BEHAVIORAL.value: 0.85,
                },
            },
        )
        modifier_detection.setdefault(
            "rules",
            {
                PersonaModifier.TRUST_LOW.value: {
                    "keywords": ["scam", "suspicious", "fake", "not trustworthy", "risky"],
                    "metadata_flags": ["negative_feedback", "trust_incident"],
                    "keyword_weight": 0.75,
                    "metadata_weight": 0.25,
                    "threshold": 0.35,
                },
                PersonaModifier.AUTHORITY_DRIVEN.value: {
                    "keywords": ["expert", "official", "leader", "certified", "approved by"],
                    "metadata_flags": ["mentions_authority_source"],
                    "keyword_weight": 0.7,
                    "metadata_weight": 0.3,
                    "threshold": 0.35,
                },
                PersonaModifier.COMMUNITY_DRIVEN.value: {
                    "keywords": ["community", "peers", "everyone uses", "reviews", "what others say"],
                    "metadata_flags": ["community_interactions_high"],
                    "keyword_weight": 0.7,
                    "metadata_weight": 0.3,
                    "threshold": 0.35,
                },
                PersonaModifier.INDIVIDUAL_DRIVEN.value: {
                    "keywords": ["for me", "my goals", "personal", "my workflow", "my use case"],
                    "metadata_flags": ["personalized_queries_high"],
                    "keyword_weight": 0.7,
                    "metadata_weight": 0.3,
                    "threshold": 0.35,
                },
                PersonaModifier.REGULATION_SENSITIVE.value: {
                    "keywords": ["compliance", "regulation", "policy", "audit", "gdpr"],
                    "metadata_flags": ["regulated_industry", "compliance_required"],
                    "keyword_weight": 0.7,
                    "metadata_weight": 0.3,
                    "threshold": 0.35,
                },
            },
        )
        transition.setdefault("min_score_multiplier", 1.25)
        transition.setdefault("stability_window", 3)
        transition.setdefault("trust_low_speed_penalty", 0.5)

        conversion.setdefault(
            "transition_thresholds",
            {
                FunnelStage.AWARENESS.value: 0.2,
                FunnelStage.CONSIDERATION.value: 0.4,
                FunnelStage.INTENT.value: 0.6,
                FunnelStage.DECISION.value: 0.75,
                FunnelStage.CONVERSION.value: 0.9,
            },
        )
        conversion.setdefault(
            "trust",
            {
                "deltas": {
                    "repeated_interaction": 0.03,
                    "clarification_success": 0.05,
                    "objection": -0.04,
                    "confusion": -0.06,
                }
            },
        )
        trigger_policy.setdefault(
            "stage_trigger_map",
            {
                FunnelStage.AWARENESS.value: [TriggerType.EDUCATIONAL_NUDGE.value],
                FunnelStage.CONSIDERATION.value: [
                    TriggerType.EDUCATIONAL_NUDGE.value,
                    TriggerType.SOCIAL_PROOF.value,
                ],
                FunnelStage.INTENT.value: [
                    TriggerType.SOCIAL_PROOF.value,
                    TriggerType.URGENCY_PROMPT.value,
                ],
                FunnelStage.DECISION.value: [
                    TriggerType.URGENCY_PROMPT.value,
                    TriggerType.CTA_OFFER.value,
                ],
                FunnelStage.CONVERSION.value: [TriggerType.CTA_OFFER.value],
            },
        )
        return value
