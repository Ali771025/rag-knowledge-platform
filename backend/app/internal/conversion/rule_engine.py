"""Deterministic config-driven conversion decision rule engine."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.internal.conversion.conversion_rules import (
    ConversionDecisionAction,
    ConversionDecisionPolicyConfig,
    ConversionDecisionRule,
    load_default_conversion_decision_policy,
)
from app.internal.conversion.policy_enums import EconomicSuggestionStrength, JourneyStage


class ConversionDecisionAllowedAction(str, Enum):
    """Externally visible action types produced by conversion decision engine."""

    INFO_ONLY = "info_only"
    MICRO_COMMIT = "micro_commit"
    ECONOMIC_SUGGESTION = "economic_suggestion"


_STAGE_INDEX = {
    JourneyStage.ENTRY: 0,
    JourneyStage.EXPLORATION: 1,
    JourneyStage.TRUST_FORMATION: 2,
    JourneyStage.OPPORTUNITY_AWARENESS: 3,
    JourneyStage.MICRO_COMMITMENT: 4,
    JourneyStage.ECONOMIC_ACTION: 5,
}


class ConversionDecisionRuleInput(BaseModel):
    """Input contract consumed by conversion decision rule engine."""

    persona: str = Field(..., min_length=1, max_length=64)
    confidence: float = Field(..., ge=0.0, le=1.0)
    intent: str = Field(..., min_length=1, max_length=64)
    stage: JourneyStage
    trust_score: float = Field(..., ge=0.0, le=1.0)
    engagement_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rejection_count: int = Field(default=0, ge=0, le=100)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConversionDecisionRuleOutput(BaseModel):
    """Rule evaluation output for CTA permissions and explainability."""

    allowed_actions: list[ConversionDecisionAllowedAction]
    economic_suggestion_strength: EconomicSuggestionStrength
    cta_allowed: bool
    block_reason: str | None = None
    reasoning: dict[str, Any] = Field(default_factory=dict)
    matched_rules: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def safe_default(cls, reason: str = "safe_default_no_match") -> "ConversionDecisionRuleOutput":
        """Return safe fallback decision payload."""

        return cls(
            allowed_actions=[ConversionDecisionAllowedAction.INFO_ONLY],
            economic_suggestion_strength=EconomicSuggestionStrength.NONE,
            cta_allowed=False,
            block_reason=reason,
            reasoning={"fallback": True, "reason": reason},
            matched_rules=[],
        )


class ConversionDecisionRuleEngine:
    """Evaluate YAML-defined conversion rules with deterministic priority order."""

    def __init__(self, policy: ConversionDecisionPolicyConfig | None = None) -> None:
        self.policy = policy or load_default_conversion_decision_policy()

    def evaluate(self, data: ConversionDecisionRuleInput) -> ConversionDecisionRuleOutput:
        """Evaluate decision rules and produce explainable CTA permissions."""

        persona = data.persona.strip().lower()
        intent = data.intent.strip().lower()
        matched_rules: list[str] = []
        evaluated: list[dict[str, Any]] = []

        allowed: list[ConversionDecisionAllowedAction] = [ConversionDecisionAllowedAction.INFO_ONLY]
        strength = EconomicSuggestionStrength.NONE
        block_reason: str | None = None
        economic_prohibited = False

        sorted_rules = sorted(self.policy.rules, key=lambda item: item.priority)
        for rule in sorted_rules:
            matched = self._matches(rule, data=data, persona=persona, intent=intent)
            evaluated.append({"id": rule.id, "priority": rule.priority, "matched": matched})
            if not matched:
                continue

            matched_rules.append(rule.id)
            action = rule.action

            if action is ConversionDecisionAction.BLOCK_ALL:
                allowed = [ConversionDecisionAllowedAction.INFO_ONLY]
                strength = EconomicSuggestionStrength.NONE
                block_reason = rule.id
                economic_prohibited = True
                break

            if action is ConversionDecisionAction.BLOCK_ECONOMIC:
                economic_prohibited = True
                allowed = [item for item in allowed if item is not ConversionDecisionAllowedAction.ECONOMIC_SUGGESTION]
                strength = EconomicSuggestionStrength.NONE
                block_reason = block_reason or rule.id
                continue

            if action is ConversionDecisionAction.ALLOW_MICRO_COMMIT_ONLY:
                allowed = [
                    ConversionDecisionAllowedAction.INFO_ONLY,
                    ConversionDecisionAllowedAction.MICRO_COMMIT,
                ]
                strength = EconomicSuggestionStrength.NONE
                block_reason = None
                continue

            if action is ConversionDecisionAction.ALLOW_ECONOMIC:
                if economic_prohibited:
                    block_reason = block_reason or "economic_blocked_by_stage_gate"
                    continue
                allowed = [
                    ConversionDecisionAllowedAction.INFO_ONLY,
                    ConversionDecisionAllowedAction.MICRO_COMMIT,
                    ConversionDecisionAllowedAction.ECONOMIC_SUGGESTION,
                ]
                strength = EconomicSuggestionStrength.MEDIUM
                block_reason = None
                continue

            if action is ConversionDecisionAction.SOFTEN_ECONOMIC:
                if ConversionDecisionAllowedAction.ECONOMIC_SUGGESTION in allowed:
                    strength = EconomicSuggestionStrength.SOFT
                continue

        # Stage gating and safety cleanup should never allow economic when prohibited.
        if economic_prohibited and ConversionDecisionAllowedAction.ECONOMIC_SUGGESTION in allowed:
            allowed = [item for item in allowed if item is not ConversionDecisionAllowedAction.ECONOMIC_SUGGESTION]
            strength = EconomicSuggestionStrength.NONE

        cta_allowed = any(
            item in allowed
            for item in (
                ConversionDecisionAllowedAction.MICRO_COMMIT,
                ConversionDecisionAllowedAction.ECONOMIC_SUGGESTION,
            )
        )
        if not matched_rules:
            block_reason = "safe_default_no_match"
        elif not cta_allowed and block_reason is None:
            block_reason = "cta_not_allowed_after_rule_evaluation"

        return ConversionDecisionRuleOutput(
            allowed_actions=allowed,
            economic_suggestion_strength=strength,
            cta_allowed=cta_allowed,
            block_reason=block_reason,
            matched_rules=matched_rules,
            reasoning={
                "evaluated_rules": evaluated,
                "matched_rules": matched_rules,
                "final_allowed_actions": [item.value for item in allowed],
                "economic_prohibited": economic_prohibited,
            },
        )

    @staticmethod
    def _matches(
        rule: ConversionDecisionRule,
        *,
        data: ConversionDecisionRuleInput,
        persona: str,
        intent: str,
    ) -> bool:
        condition = rule.condition

        if condition.trust_score_lt is not None and not (data.trust_score < condition.trust_score_lt):
            return False
        if condition.trust_score_gte is not None and not (data.trust_score >= condition.trust_score_gte):
            return False
        if condition.confidence_gt is not None and not (data.confidence > condition.confidence_gt):
            return False

        if condition.stage_lt is not None and not (_STAGE_INDEX[data.stage] < _STAGE_INDEX[condition.stage_lt]):
            return False
        if condition.stage_gte is not None and not (_STAGE_INDEX[data.stage] >= _STAGE_INDEX[condition.stage_gte]):
            return False

        if condition.persona is not None and persona != condition.persona:
            return False
        if condition.persona_in and persona not in set(condition.persona_in):
            return False
        if condition.intent is not None and intent != condition.intent.strip().lower():
            return False
        if condition.rejection_count_gte is not None and not (data.rejection_count >= condition.rejection_count_gte):
            return False

        return True
