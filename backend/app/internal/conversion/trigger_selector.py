"""Deterministic, policy-driven trigger selection engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from app.internal.conversion.policy_enums import JourneyStage, PsychologicalTrigger


@dataclass(frozen=True, slots=True)
class TriggerSelectionInput:
    """Inputs used by trigger policy selection rules."""

    persona_label: str
    stage: JourneyStage
    trust_score: float
    intent: str


@dataclass(frozen=True, slots=True)
class TriggerSelectionResult:
    """Trigger selection output with orchestration metadata only."""

    primary_trigger: PsychologicalTrigger
    secondary_trigger: PsychologicalTrigger | None
    reason: str
    metadata: dict[str, str]


@dataclass(frozen=True, slots=True)
class TriggerSelectionConfig:
    """Configurable stage/persona rules for deterministic trigger selection."""

    stage_priority: Mapping[JourneyStage, tuple[PsychologicalTrigger, ...]] = field(
        default_factory=lambda: {
            JourneyStage.ENTRY: (PsychologicalTrigger.CURIOSITY, PsychologicalTrigger.CONTROL),
            JourneyStage.EXPLORATION: (PsychologicalTrigger.CURIOSITY, PsychologicalTrigger.FUTURE_SELF),
            JourneyStage.TRUST_FORMATION: (PsychologicalTrigger.SOCIAL_PROOF, PsychologicalTrigger.AUTHORITY),
            JourneyStage.OPPORTUNITY_AWARENESS: (PsychologicalTrigger.LOSS_AVOIDANCE, PsychologicalTrigger.FUTURE_SELF),
            JourneyStage.MICRO_COMMITMENT: (PsychologicalTrigger.MICRO_COMMITMENT, PsychologicalTrigger.CONTROL),
            JourneyStage.ECONOMIC_ACTION: (PsychologicalTrigger.SCARCITY, PsychologicalTrigger.LOSS_AVOIDANCE),
        }
    )
    persona_bias: Mapping[str, tuple[PsychologicalTrigger, ...]] = field(
        default_factory=lambda: {
            "saver": (PsychologicalTrigger.LOSS_AVOIDANCE, PsychologicalTrigger.CONTROL),
            "hunter": (PsychologicalTrigger.SCARCITY, PsychologicalTrigger.FUTURE_SELF),
            "architect": (PsychologicalTrigger.AUTHORITY, PsychologicalTrigger.FUTURE_SELF),
            "explorer": (PsychologicalTrigger.CURIOSITY, PsychologicalTrigger.SOCIAL_PROOF),
        }
    )
    intent_bias: Mapping[str, PsychologicalTrigger] = field(
        default_factory=lambda: {
            "review": PsychologicalTrigger.SOCIAL_PROOF,
            "authority": PsychologicalTrigger.AUTHORITY,
            "control": PsychologicalTrigger.CONTROL,
            "future": PsychologicalTrigger.FUTURE_SELF,
            "trial": PsychologicalTrigger.MICRO_COMMITMENT,
            "pricing": PsychologicalTrigger.LOSS_AVOIDANCE,
        }
    )
    low_trust_threshold: float = 0.30
    secondary_min_trust: float = 0.35
    fallback_trigger: PsychologicalTrigger = PsychologicalTrigger.CURIOSITY


class TriggerSelectionEngine:
    """Select at most two deterministic triggers from policy rules."""

    def __init__(self, config: TriggerSelectionConfig | None = None) -> None:
        self.config = config or TriggerSelectionConfig()

    def select(self, data: TriggerSelectionInput) -> TriggerSelectionResult:
        """Select primary + optional secondary trigger with safe fallback behavior."""

        persona_key = data.persona_label.strip().lower()
        intent_text = data.intent.strip().lower()

        ordered: list[PsychologicalTrigger] = []

        # Persona bias first for personalization.
        for trig in self.config.persona_bias.get(persona_key, ()):  # deterministic order
            if trig not in ordered:
                ordered.append(trig)

        # Stage baseline rules.
        for trig in self.config.stage_priority.get(data.stage, ()):  # deterministic order
            if trig not in ordered:
                ordered.append(trig)

        # Intent-specific bias appended.
        for token, trig in self.config.intent_bias.items():
            if token in intent_text and trig not in ordered:
                ordered.append(trig)

        if not ordered:
            ordered = [self.config.fallback_trigger]

        # Safe fallback: avoid aggressive scarcity under low trust.
        if data.trust_score < self.config.low_trust_threshold:
            ordered = [tr for tr in ordered if tr is not PsychologicalTrigger.SCARCITY]
            if not ordered:
                ordered = [self.config.fallback_trigger]

        primary = ordered[0]
        secondary = None
        if data.trust_score >= self.config.secondary_min_trust:
            for trig in ordered[1:]:
                if trig is not primary:
                    secondary = trig
                    break

        return TriggerSelectionResult(
            primary_trigger=primary,
            secondary_trigger=secondary,
            reason="deterministic_policy_selection",
            metadata={
                "persona": persona_key or "unknown",
                "stage": data.stage.value,
                "trust_score": f"{data.trust_score:.3f}",
                "secondary_enabled": str(data.trust_score >= self.config.secondary_min_trust).lower(),
            },
        )
