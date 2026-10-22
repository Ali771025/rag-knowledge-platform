"""Deterministic confidence scoring and response strategy selection."""

from __future__ import annotations

from app.config.guardrails import (
    CONFIDENCE_MIN_SCORE,
    CONFIDENCE_NORMAL_SCORE,
    CONFIDENCE_REJECT_SCORE,
)

_DISCLAIMER_PREFIX = {
    "fa": "بر اساس اطلاعات موجود، ",
    "en": "Based on the available information, ",
}


def calculate_confidence(
    retrieval_score: float,
    intent_score: float,
    grounding_score: float,
) -> float:
    """Calculate weighted confidence and clamp to [0.0, 1.0]."""
    confidence = (
        (retrieval_score * 0.5)
        + (intent_score * 0.2)
        + (grounding_score * 0.3)
    )
    return round(max(0.0, min(1.0, confidence)), 4)


def determine_response_strategy(confidence_score: float) -> str:
    """Return response strategy using centralized confidence thresholds."""
    if confidence_score >= CONFIDENCE_NORMAL_SCORE:
        return "answer"
    if confidence_score >= CONFIDENCE_MIN_SCORE:
        return "answer_with_disclaimer"
    if confidence_score >= CONFIDENCE_REJECT_SCORE:
        return "clarify"
    return "reject"


def apply_uncertainty_disclaimer(response: str, language: str = "fa") -> str:
    """Prefix response with a bilingual uncertainty disclaimer."""
    prefix = _DISCLAIMER_PREFIX.get(language.lower(), _DISCLAIMER_PREFIX["en"])
    return f"{prefix}{response}"

