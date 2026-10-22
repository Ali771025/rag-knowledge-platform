"""Rule-based persona modifier detection for orchestration policy layers."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from app.internal.persona.enums import PersonaModifier
from app.internal.policy.config_models import ModifierRuleConfig


@dataclass(frozen=True, slots=True)
class ModifierEvaluation:
    """Explainable evaluation payload for one persona modifier."""

    modifier: PersonaModifier
    score: float
    threshold: float
    is_active: bool
    keyword_hits: tuple[str, ...]
    metadata_hits: tuple[str, ...]
    explanation: str


@dataclass(frozen=True, slots=True)
class ModifierDetectionResult:
    """Detected modifier set plus explainable per-modifier observability details."""

    active_modifiers: tuple[PersonaModifier, ...]
    evaluations: Mapping[PersonaModifier, ModifierEvaluation]


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase.lower())}\b", text) is not None


def detect_persona_modifiers(
    *,
    message: str,
    metadata: Mapping[str, Any] | None,
    rules: Mapping[PersonaModifier, ModifierRuleConfig],
) -> ModifierDetectionResult:
    """Detect active modifiers from message text and metadata flags using configured rules."""

    normalized = re.sub(r"\s+", " ", message.strip().lower())
    safe_metadata = metadata or {}

    evaluations: dict[PersonaModifier, ModifierEvaluation] = {}
    active: list[PersonaModifier] = []

    for modifier, rule in rules.items():
        keyword_hits = tuple(keyword for keyword in rule.keywords if _contains_phrase(normalized, keyword))
        metadata_hits = tuple(
            flag
            for flag in rule.metadata_flags
            if bool(safe_metadata.get(flag, False))
        )

        keyword_component = rule.keyword_weight * (len(keyword_hits) / max(1, len(rule.keywords)))
        metadata_component = rule.metadata_weight * (len(metadata_hits) / max(1, len(rule.metadata_flags)))
        score = min(1.0, keyword_component + metadata_component)

        is_active = score >= rule.threshold
        explanation = (
            f"keywords={len(keyword_hits)}/{len(rule.keywords)} "
            f"metadata={len(metadata_hits)}/{len(rule.metadata_flags)}"
        )

        evaluation = ModifierEvaluation(
            modifier=modifier,
            score=score,
            threshold=rule.threshold,
            is_active=is_active,
            keyword_hits=keyword_hits,
            metadata_hits=metadata_hits,
            explanation=explanation,
        )
        evaluations[modifier] = evaluation
        if is_active:
            active.append(modifier)

    return ModifierDetectionResult(active_modifiers=tuple(active), evaluations=evaluations)
