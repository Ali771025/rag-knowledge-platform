"""Config-driven persona scoring using deterministic weighted signal aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from app.internal.persona.enums import PersonaType
from app.internal.persona.signal_models import ExtractedPersonaSignals, PersonaSignal


@dataclass(frozen=True, slots=True)
class SignalContribution:
    """Explainable contribution row for one signal in one message position."""

    signal: PersonaSignal
    weight: float
    intensity: float
    decay_factor: float
    contribution: float
    message_index: int


@dataclass(frozen=True, slots=True)
class PersonaScoreBreakdown:
    """Detailed per-persona score aggregation and contribution details."""

    persona_type: PersonaType
    raw_score: float
    normalized_score: float
    contributions: tuple[SignalContribution, ...]


@dataclass(frozen=True, slots=True)
class PersonaScoringResult:
    """Final scoring output for observability and downstream persona decisions."""

    dominant_persona: PersonaType
    persona_scores: Mapping[PersonaType, float]
    breakdown: Mapping[PersonaType, PersonaScoreBreakdown]


def score_persona_signals(
    history: Sequence[ExtractedPersonaSignals],
    signal_weights: Mapping[PersonaType, Mapping[PersonaSignal, float]],
    decay_factor_base: float,
) -> PersonaScoringResult:
    """Score persona likelihood by summing ``weight * intensity * decay`` across history."""

    if decay_factor_base < 0.0 or decay_factor_base > 1.0:
        raise ValueError("decay_factor_base must be between 0.0 and 1.0")

    if not history:
        zero_scores = {persona: 0.0 for persona in PersonaType}
        breakdown = {
            persona: PersonaScoreBreakdown(
                persona_type=persona,
                raw_score=0.0,
                normalized_score=0.0,
                contributions=(),
            )
            for persona in PersonaType
        }
        return PersonaScoringResult(
            dominant_persona=PersonaType.EXPLORER,
            persona_scores=zero_scores,
            breakdown=breakdown,
        )

    raw_scores: dict[PersonaType, float] = {persona: 0.0 for persona in PersonaType}
    contributions_by_persona: dict[PersonaType, list[SignalContribution]] = {persona: [] for persona in PersonaType}

    history_len = len(history)
    for message_index, extracted in enumerate(history):
        age = history_len - 1 - message_index
        decay_factor = decay_factor_base ** age
        normalized = extracted.normalized_signals()

        for persona in PersonaType:
            persona_weights = signal_weights.get(persona, {})
            for signal in PersonaSignal:
                weight = float(persona_weights.get(signal, 0.0))
                intensity = float(normalized.get(signal, 0.0))
                contribution = weight * intensity * decay_factor
                raw_scores[persona] += contribution
                contributions_by_persona[persona].append(
                    SignalContribution(
                        signal=signal,
                        weight=weight,
                        intensity=intensity,
                        decay_factor=decay_factor,
                        contribution=contribution,
                        message_index=message_index,
                    )
                )

    min_score = min(raw_scores.values())
    shifted = {persona: score - min_score for persona, score in raw_scores.items()}
    total_shifted = sum(shifted.values())
    if total_shifted <= 0.0:
        normalized_scores = {persona: 0.0 for persona in PersonaType}
    else:
        normalized_scores = {persona: value / total_shifted for persona, value in shifted.items()}

    breakdown = {
        persona: PersonaScoreBreakdown(
            persona_type=persona,
            raw_score=raw_scores[persona],
            normalized_score=normalized_scores[persona],
            contributions=tuple(contributions_by_persona[persona]),
        )
        for persona in PersonaType
    }

    dominant_persona = max(PersonaType, key=lambda persona: raw_scores[persona])
    return PersonaScoringResult(
        dominant_persona=dominant_persona,
        persona_scores=normalized_scores,
        breakdown=breakdown,
    )
