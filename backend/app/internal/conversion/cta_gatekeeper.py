"""CTA gatekeeper facade around conversion policy decisions."""

from __future__ import annotations

from dataclasses import dataclass

from app.internal.conversion.conversion_policy import (
    ConversionPolicyConfig,
    ConversionPolicyInput,
    ConversionPolicyResult,
    evaluate_conversion_policy,
)
from app.internal.conversion.policy_enums import CTAAction


@dataclass(frozen=True, slots=True)
class CTAGatekeeperDecision:
    """Gatekeeper output with preferred action and policy explainability."""

    allowed_actions: tuple[CTAAction, ...]
    preferred_action: CTAAction | None
    blocked_reasons: tuple[str, ...]
    explanation: dict[str, str]


class CTAGatekeeper:
    """Thin deterministic gatekeeper that applies configured conversion policy."""

    def __init__(self, config: ConversionPolicyConfig | None = None) -> None:
        self.config = config or ConversionPolicyConfig()

    def evaluate(self, policy_input: ConversionPolicyInput) -> CTAGatekeeperDecision:
        """Evaluate CTA permissions and select preferred allowed action."""

        result: ConversionPolicyResult = evaluate_conversion_policy(policy_input, self.config)
        preferred = result.allowed_actions[0] if result.allowed_actions else None
        return CTAGatekeeperDecision(
            allowed_actions=result.allowed_actions,
            preferred_action=preferred,
            blocked_reasons=result.blocked_reasons,
            explanation=result.explanation,
        )
