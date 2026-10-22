"""Persona confidence evaluation and neutral fallback assignment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.internal.persona.enums import PersonaType


NEUTRAL_ASSIGNMENT = "NEUTRAL"


@dataclass(frozen=True, slots=True)
class PersonaConfidenceResult:
    """Packaged confidence decision for downstream persona orchestration."""

    assigned_persona: PersonaType | None
    assignment_label: str
    top_persona: PersonaType | None
    second_persona: PersonaType | None
    top_score: float
    second_score: float
    confidence_gap: float
    threshold: float
    is_low_confidence: bool


def evaluate_persona_confidence(
    persona_scores: Mapping[PersonaType, float],
    threshold: float,
) -> PersonaConfidenceResult:
    """Evaluate confidence via top-two score gap and apply neutral fallback."""

    if threshold < 0.0 or threshold > 1.0:
        raise ValueError("threshold must be between 0.0 and 1.0")

    ranked = sorted(persona_scores.items(), key=lambda item: item[1], reverse=True)
    if not ranked:
        return PersonaConfidenceResult(
            assigned_persona=None,
            assignment_label=NEUTRAL_ASSIGNMENT,
            top_persona=None,
            second_persona=None,
            top_score=0.0,
            second_score=0.0,
            confidence_gap=0.0,
            threshold=threshold,
            is_low_confidence=True,
        )

    top_persona, top_score = ranked[0]
    if len(ranked) >= 2:
        second_persona, second_score = ranked[1]
    else:
        second_persona, second_score = None, 0.0

    confidence_gap = float(top_score) - float(second_score)
    is_low_confidence = confidence_gap < threshold

    if is_low_confidence:
        return PersonaConfidenceResult(
            assigned_persona=None,
            assignment_label=NEUTRAL_ASSIGNMENT,
            top_persona=top_persona,
            second_persona=second_persona,
            top_score=float(top_score),
            second_score=float(second_score),
            confidence_gap=confidence_gap,
            threshold=threshold,
            is_low_confidence=True,
        )

    return PersonaConfidenceResult(
        assigned_persona=top_persona,
        assignment_label=top_persona.value,
        top_persona=top_persona,
        second_persona=second_persona,
        top_score=float(top_score),
        second_score=float(second_score),
        confidence_gap=confidence_gap,
        threshold=threshold,
        is_low_confidence=False,
    )
