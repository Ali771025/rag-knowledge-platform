from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from app.qora.config import QoraPolicyConfig, load_qora_policy
from app.qora.domain.contracts import ModifierDecision, SignalCandidate
from app.qora.domain.enums import PersonaModifier
from app.qora.domain.signals.taxonomy import SIGNAL_TAXONOMY


@dataclass(frozen=True, slots=True)
class ModifierEvaluationResult:
    decisions: tuple[ModifierDecision, ...]
    active_modifiers: tuple[PersonaModifier, ...]


class ModifierEngine:
    def __init__(self, policy: QoraPolicyConfig | None = None) -> None:
        self.policy = policy or load_qora_policy()

    def evaluate(
        self,
        *,
        signals: Sequence[SignalCandidate],
        currently_active: Sequence[PersonaModifier] = (),
        active_turns: Mapping[PersonaModifier, int] | None = None,
    ) -> ModifierEvaluationResult:
        active_set = set(currently_active)
        durations = active_turns or {}
        decisions: list[ModifierDecision] = []
        next_active: list[PersonaModifier] = []
        for modifier in PersonaModifier:
            relevant = [
                signal
                for signal in signals
                if (definition := SIGNAL_TAXONOMY.get(signal.code)) is not None and definition.modifier == modifier
            ]
            score = 1.0
            for signal in relevant:
                score *= 1.0 - signal.strength
            score = 1.0 - score
            rule = self.policy.modifier_rules[modifier.value]
            if modifier in active_set:
                minimum_held = durations.get(modifier, 0) >= rule.minimum_duration_turns
                is_active = not (minimum_held and score < rule.deactivation_threshold)
            else:
                is_active = score >= rule.activation_threshold
            if is_active:
                next_active.append(modifier)
            decisions.append(
                ModifierDecision(
                    name=modifier,
                    score=round(score, 6),
                    active=is_active,
                    evidence=[signal.code for signal in relevant],
                    response_effect=rule.effect,
                )
            )
        return ModifierEvaluationResult(tuple(decisions), tuple(next_active))

