"""Deterministic psychological trigger selector driven by YAML policy."""

from __future__ import annotations

from typing import Any

from app.internal.conversion.policy_enums import TriggerType
from app.internal.persona.enums import PersonaModifier
from app.prompt_orchestration.models import TriggerSelectionInput, TriggerSelectionOutput
from app.prompt_orchestration.trigger_policy import TriggerPolicyConfig, load_default_trigger_policy


_INTENT_TOKENS = {
    "explorer": {"explorer", "exploration", "discover"},
    "skeptic": {"skeptic", "skeptical", "doubt"},
    "investor": {"investor", "investment", "invest", "roi"},
}


class TriggerSelector:
    """Policy-driven trigger selector with deterministic rule ordering."""

    def __init__(self, policy: TriggerPolicyConfig | None = None) -> None:
        self.policy = policy or load_default_trigger_policy()

    def select(self, data: TriggerSelectionInput) -> TriggerSelectionOutput:
        """Select primary and optional secondary triggers with reasoning metadata."""

        persona = data.persona.strip().lower()
        intent = data.intent.strip().lower()
        intent_tags = self._intent_tags(intent)
        modifiers = set(data.modifiers)
        trust_low = PersonaModifier.TRUST_LOW in modifiers
        usage = data.session_trigger_usage
        rejections = data.rejection_history
        capacity_flags = data.capacity_flags
        reasoning: dict[str, Any] = {
            "persona": persona,
            "intent_tags": sorted(intent_tags),
            "trust_low_modifier": trust_low,
            "applied_rules": [],
        }

        candidates = self._guidance_candidates(persona=persona, intent_tags=intent_tags)
        reasoning["candidate_order"] = [trigger.value for trigger in candidates]

        allowed_candidates: list[TriggerType] = []
        for trigger in candidates:
            if trigger is TriggerType.SCARCITY and data.trust_score < self.policy.scarcity_min_trust:
                control = TriggerType.CONTROL
                if self._is_allowed(
                    trigger=control,
                    persona=persona,
                    data=data,
                    modifiers=modifiers,
                    usage=usage,
                    capacity_flags=capacity_flags,
                ):
                    if control not in allowed_candidates:
                        allowed_candidates.append(control)
                    reasoning["applied_rules"].append("scarcity_low_trust_fallback_to_control")
                continue
            if self._is_allowed(
                trigger=trigger,
                persona=persona,
                data=data,
                modifiers=modifiers,
                usage=usage,
                capacity_flags=capacity_flags,
            ):
                allowed_candidates.append(trigger)

        if trust_low:
            transparency = TriggerType.TRANSPARENCY
            if transparency in self.policy.trigger_policies and self._is_allowed(
                trigger=transparency,
                persona=persona,
                data=data,
                modifiers=modifiers,
                usage=usage,
                capacity_flags=capacity_flags,
            ):
                allowed_candidates = [transparency, *[item for item in allowed_candidates if item is not transparency]]
                reasoning["applied_rules"].append("trust_low_prefers_transparency")

        selected = self._choose_with_fallbacks(
            allowed_candidates=allowed_candidates,
            persona=persona,
            data=data,
            modifiers=modifiers,
            usage=usage,
            capacity_flags=capacity_flags,
            rejections=rejections,
            reasoning=reasoning,
        )

        max_count = min(self.policy.max_triggers_per_response, 2)
        selected = selected[:max_count]
        if not selected:
            fallback = TriggerType.CURIOSITY
            if not self._is_allowed(
                trigger=fallback,
                persona=persona,
                data=data,
                modifiers=modifiers,
                usage=usage,
                capacity_flags=capacity_flags,
            ):
                selected = []
                for trigger in self.policy.trigger_policies:
                    if self._is_allowed(
                        trigger=trigger,
                        persona=persona,
                        data=data,
                        modifiers=modifiers,
                        usage=usage,
                        capacity_flags=capacity_flags,
                    ):
                        selected = [trigger]
                        break
            else:
                selected = [fallback]
            reasoning["applied_rules"].append("safe_fallback_used")

        intensity = self._compute_intensity(
            persona=persona,
            trust_low=trust_low,
            selected=selected,
            rejections=rejections,
            reasoning=reasoning,
        )

        secondary = selected[1] if len(selected) > 1 else None
        return TriggerSelectionOutput(
            primary_trigger=selected[0],
            secondary_trigger=secondary,
            intensity=intensity,
            selected_triggers=selected,
            reasoning=reasoning,
        )

    @staticmethod
    def _intent_tags(intent: str) -> set[str]:
        tags: set[str] = set()
        for tag, candidates in _INTENT_TOKENS.items():
            if any(token in intent for token in candidates):
                tags.add(tag)
        return tags

    @staticmethod
    def _guidance_candidates(persona: str, intent_tags: set[str]) -> list[TriggerType]:
        ordered: list[TriggerType] = []

        def push(trigger: TriggerType) -> None:
            if trigger not in ordered:
                ordered.append(trigger)

        if persona == "saver" and ("explorer" in intent_tags or "skeptic" in intent_tags):
            for trigger in (TriggerType.CONTROL, TriggerType.TRANSPARENCY, TriggerType.SOCIAL_PROOF):
                push(trigger)
        elif persona == "hunter" and "investor" in intent_tags:
            for trigger in (TriggerType.OPPORTUNITY_FRAMING, TriggerType.SCARCITY, TriggerType.MICRO_COMMITMENT):
                push(trigger)
        elif persona == "player" and "explorer" in intent_tags:
            for trigger in (TriggerType.CURIOSITY, TriggerType.MICRO_COMMITMENT):
                push(trigger)
        elif persona == "architect" and "investor" in intent_tags:
            for trigger in (TriggerType.TRANSPARENCY, TriggerType.CONTROL, TriggerType.OPPORTUNITY_FRAMING):
                push(trigger)
        elif persona in {"neutral", "unknown"}:
            for trigger in (TriggerType.CURIOSITY, TriggerType.TRANSPARENCY):
                push(trigger)

        if not ordered:
            for trigger in (TriggerType.CURIOSITY, TriggerType.TRANSPARENCY, TriggerType.CONTROL):
                push(trigger)

        return ordered

    def _is_allowed(
        self,
        *,
        trigger: TriggerType,
        persona: str,
        data: TriggerSelectionInput,
        modifiers: set[PersonaModifier],
        usage: dict[TriggerType, int],
        capacity_flags: dict[TriggerType, bool],
        ignore_required_modifiers: bool = False,
    ) -> bool:
        rule = self.policy.trigger_policies.get(trigger)
        if rule is None:
            return False

        if data.stage not in rule.allowed_stages:
            return False

        if "all" not in rule.allowed_personas and persona not in rule.allowed_personas:
            return False

        if not ignore_required_modifiers and any(modifier not in modifiers for modifier in rule.required_modifiers):
            return False

        min_trust = rule.min_trust
        if trigger is TriggerType.SCARCITY:
            min_trust = max(min_trust, self.policy.scarcity_min_trust)
        if data.trust_score < min_trust:
            return False

        if usage.get(trigger, 0) >= rule.max_per_session:
            return False

        if rule.requires_real_capacity_limit and not capacity_flags.get(trigger, False):
            return False

        return True

    def _choose_with_fallbacks(
        self,
        *,
        allowed_candidates: list[TriggerType],
        persona: str,
        data: TriggerSelectionInput,
        modifiers: set[PersonaModifier],
        usage: dict[TriggerType, int],
        capacity_flags: dict[TriggerType, bool],
        rejections: dict[TriggerType, int],
        reasoning: dict[str, Any],
    ) -> list[TriggerType]:
        selected: list[TriggerType] = []
        for candidate in allowed_candidates:
            trigger = candidate
            rule = self.policy.trigger_policies.get(candidate)
            rejection_count = rejections.get(candidate, 0)

            if rejection_count >= 2 and rule is not None and rule.softer_fallback is not None:
                resistance_hits = reasoning.setdefault("resistance_hits", [])
                if candidate.value not in resistance_hits:
                    resistance_hits.append(candidate.value)
                fallback = rule.softer_fallback
                if self._is_allowed(
                    trigger=fallback,
                    persona=persona,
                    data=data,
                    modifiers=modifiers,
                    usage=usage,
                    capacity_flags=capacity_flags,
                    ignore_required_modifiers=True,
                ):
                    trigger = fallback
                    reasoning["applied_rules"].append(f"rejection_fallback_{candidate.value}_to_{fallback.value}")

            if trigger not in selected:
                selected.append(trigger)
            if len(selected) >= 2:
                break

        return selected

    def _compute_intensity(
        self,
        *,
        persona: str,
        trust_low: bool,
        selected: list[TriggerType],
        rejections: dict[TriggerType, int],
        reasoning: dict[str, Any],
    ) -> float:
        intensity = 1.0
        if persona in {"neutral", "unknown"}:
            intensity *= 0.55
            reasoning["applied_rules"].append("neutral_low_intensity")

        if trust_low:
            intensity *= self.policy.trust_low_intensity_factor

        for trigger in selected:
            if rejections.get(trigger, 0) >= 2:
                intensity *= self.policy.resistance_decay
                reasoning["applied_rules"].append(f"resistance_decay_applied_{trigger.value}")
        for token in reasoning.get("resistance_hits", []):
            if token not in {trigger.value for trigger in selected}:
                intensity *= self.policy.resistance_decay
                reasoning["applied_rules"].append(f"resistance_decay_applied_{token}")

        return max(0.0, min(1.0, round(float(intensity), 4)))
