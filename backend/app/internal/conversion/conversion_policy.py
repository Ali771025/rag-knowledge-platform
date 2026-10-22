"""Deterministic conversion policy evaluation and CTA allowance rules."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.internal.conversion.policy_enums import CTAAction, JourneyStage


@dataclass(frozen=True, slots=True)
class ConversionPolicyInput:
    """Inputs consumed by conversion policy engine."""

    persona_label: str
    persona_confidence: float
    trust_score: float
    stage: JourneyStage
    intent: str
    is_ambiguous: bool = False


@dataclass(frozen=True, slots=True)
class ConversionPolicyResult:
    """Allowed action set and explainable blocked reasons."""

    allowed_actions: tuple[CTAAction, ...]
    blocked_reasons: tuple[str, ...]
    explanation: dict[str, str]


@dataclass(frozen=True, slots=True)
class ConversionPolicyConfig:
    """Configurable thresholds and persona rules for CTA gating decisions."""

    low_trust_threshold: float = 0.35
    economic_min_trust: float = 0.72
    economic_min_confidence: float = 0.25
    economic_personas: tuple[str, ...] = ("hunter", "architect")
    saver_persona_label: str = "saver"
    micro_stage_min: JourneyStage = JourneyStage.OPPORTUNITY_AWARENESS
    aggressive_stage_min: JourneyStage = JourneyStage.TRUST_FORMATION

    economic_intent_tokens: tuple[str, ...] = ("buy", "purchase", "pricing", "budget", "contract")


_STAGE_INDEX = {
    JourneyStage.ENTRY: 0,
    JourneyStage.EXPLORATION: 1,
    JourneyStage.TRUST_FORMATION: 2,
    JourneyStage.OPPORTUNITY_AWARENESS: 3,
    JourneyStage.MICRO_COMMITMENT: 4,
    JourneyStage.ECONOMIC_ACTION: 5,
}


def _stage_at_least(stage: JourneyStage, minimum: JourneyStage) -> bool:
    return _STAGE_INDEX[stage] >= _STAGE_INDEX[minimum]


def evaluate_conversion_policy(
    data: ConversionPolicyInput,
    config: ConversionPolicyConfig | None = None,
) -> ConversionPolicyResult:
    """Evaluate CTA permissions from trust/persona/stage/intent guard rules."""

    cfg = config or ConversionPolicyConfig()
    persona = data.persona_label.strip().lower()
    intent_text = data.intent.strip().lower()

    blocked: list[str] = []
    allowed: list[CTAAction] = []

    aggressive_blocked = (
        data.trust_score < cfg.low_trust_threshold
        or data.is_ambiguous
        or not _stage_at_least(data.stage, cfg.aggressive_stage_min)
    )
    if aggressive_blocked:
        blocked.append("aggressive_cta_blocked_low_trust_or_ambiguity_or_stage")

    # Special rule: low-trust saver gets micro commitment only.
    if persona == cfg.saver_persona_label and data.trust_score < cfg.low_trust_threshold:
        allowed.append(CTAAction.MICRO_COMMITMENT)
        return ConversionPolicyResult(
            allowed_actions=tuple(allowed),
            blocked_reasons=tuple(blocked),
            explanation={
                "rule": "low_trust_saver_micro_only",
                "trust_score": f"{data.trust_score:.3f}",
                "stage": data.stage.value,
            },
        )

    # Baseline educational action is safe if no stronger action allowed.
    if _stage_at_least(data.stage, cfg.micro_stage_min):
        allowed.append(CTAAction.MICRO_COMMITMENT)
    else:
        allowed.append(CTAAction.EDUCATIONAL)

    is_economic_persona = persona in cfg.economic_personas
    has_economic_intent = any(token in intent_text for token in cfg.economic_intent_tokens)

    if (
        is_economic_persona
        and has_economic_intent
        and data.trust_score >= cfg.economic_min_trust
        and data.persona_confidence >= cfg.economic_min_confidence
        and _stage_at_least(data.stage, JourneyStage.MICRO_COMMITMENT)
        and not aggressive_blocked
    ):
        allowed.insert(0, CTAAction.ECONOMIC)
    else:
        blocked.append("economic_cta_requirements_not_met")

    return ConversionPolicyResult(
        allowed_actions=tuple(dict.fromkeys(allowed))[:2],
        blocked_reasons=tuple(dict.fromkeys(blocked)),
        explanation={
            "persona": persona or "unknown",
            "trust_score": f"{data.trust_score:.3f}",
            "stage": data.stage.value,
            "economic_persona": str(is_economic_persona).lower(),
            "economic_intent": str(has_economic_intent).lower(),
        },
    )
