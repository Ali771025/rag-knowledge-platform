"""Deterministic trust score engine for funnel progression support."""

from __future__ import annotations

from dataclasses import dataclass

from app.internal.policy.config_models import TrustDeltaConfig


@dataclass(frozen=True, slots=True)
class TrustScoreReason:
    """Explanation row for one trust score delta application."""

    code: str
    delta: float
    detail: str


@dataclass(frozen=True, slots=True)
class TrustScoreResult:
    """Updated bounded trust score plus applied delta explanations."""

    previous_score: float
    updated_score: float
    applied_delta: float
    reasons: tuple[TrustScoreReason, ...]


def update_trust_score(
    *,
    current_score: float,
    repeated_interaction_count: int,
    clarification_success_count: int,
    objection_count: int,
    confusion_count: int,
    deltas: TrustDeltaConfig,
) -> TrustScoreResult:
    """Apply configurable trust deltas and clamp the score into [0.0, 1.0]."""

    if current_score < 0.0 or current_score > 1.0:
        raise ValueError("current_score must be between 0.0 and 1.0")

    repeated = max(0, repeated_interaction_count)
    clarifications = max(0, clarification_success_count)
    objections = max(0, objection_count)
    confusion = max(0, confusion_count)

    reasons: list[TrustScoreReason] = []
    total_delta = 0.0

    if repeated > 0:
        delta = repeated * deltas.repeated_interaction
        total_delta += delta
        reasons.append(
            TrustScoreReason(
                code="repeated_interaction",
                delta=delta,
                detail=f"count={repeated}",
            )
        )

    if clarifications > 0:
        delta = clarifications * deltas.clarification_success
        total_delta += delta
        reasons.append(
            TrustScoreReason(
                code="clarification_success",
                delta=delta,
                detail=f"count={clarifications}",
            )
        )

    if objections > 0:
        delta = objections * deltas.objection
        total_delta += delta
        reasons.append(
            TrustScoreReason(
                code="objection",
                delta=delta,
                detail=f"count={objections}",
            )
        )

    if confusion > 0:
        delta = confusion * deltas.confusion
        total_delta += delta
        reasons.append(
            TrustScoreReason(
                code="confusion",
                delta=delta,
                detail=f"count={confusion}",
            )
        )

    updated = min(1.0, max(0.0, current_score + total_delta))
    return TrustScoreResult(
        previous_score=current_score,
        updated_score=updated,
        applied_delta=updated - current_score,
        reasons=tuple(reasons),
    )
