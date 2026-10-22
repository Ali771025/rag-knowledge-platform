from __future__ import annotations

from typing import Sequence

from app.qora.domain.contracts import DepthPolicy
from app.qora.domain.enums import DepthLevel, PersonaCore, PersonaModifier


class DepthController:
    """Deterministic response-shape policy; it does not generate response text."""

    def resolve(
        self,
        *,
        persona: PersonaCore | None,
        modifiers: Sequence[PersonaModifier],
        confidence: float,
    ) -> DepthPolicy:
        modifier_set = set(modifiers)
        cautious = PersonaModifier.REGULATION_SENSITIVE in modifier_set
        if PersonaModifier.TRUST_LOW in modifier_set:
            level = DepthLevel.LOW if persona != PersonaCore.SAVER else DepthLevel.MEDIUM
        elif persona == PersonaCore.ARCHITECT and PersonaModifier.AUTHORITY_DRIVEN in modifier_set:
            level = DepthLevel.HIGH
        elif cautious:
            level = DepthLevel.HIGH if persona == PersonaCore.ARCHITECT else DepthLevel.MEDIUM
        elif persona in {PersonaCore.HUNTER, PersonaCore.PLAYER, PersonaCore.SAVER}:
            level = DepthLevel.MEDIUM
        elif persona == PersonaCore.ARCHITECT:
            level = DepthLevel.HIGH
        else:
            level = DepthLevel.LOW
        if confidence < 0.5:
            level = DepthLevel.LOW
        return self._policy(level, cautious=cautious or PersonaModifier.TRUST_LOW in modifier_set)

    @staticmethod
    def _policy(level: DepthLevel, *, cautious: bool) -> DepthPolicy:
        if level == DepthLevel.HIGH:
            return DepthPolicy(
                level=level, answer_length="long", technical_vocabulary="advanced", number_of_reasons=4,
                number_of_sources=3, number_of_options=2, cta_intensity="low" if cautious else "medium",
                detail_level="deep", risk_disclosure_depth="deep", architecture_detail="deep", cautious_tone=cautious,
            )
        if level == DepthLevel.MEDIUM:
            return DepthPolicy(
                level=level, answer_length="medium", technical_vocabulary="moderate", number_of_reasons=3,
                number_of_sources=2, number_of_options=2, cta_intensity="low" if cautious else "medium",
                detail_level="balanced", risk_disclosure_depth="balanced", architecture_detail="summary", cautious_tone=cautious,
            )
        return DepthPolicy(
            level=level, answer_length="short", technical_vocabulary="plain", number_of_reasons=2,
            number_of_sources=1, number_of_options=1, cta_intensity="none" if cautious else "low",
            detail_level="essential", risk_disclosure_depth="essential", architecture_detail="none", cautious_tone=cautious,
        )
