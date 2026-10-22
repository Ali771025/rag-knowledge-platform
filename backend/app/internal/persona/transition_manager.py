"""Deterministic persona transition manager using rolling Redis evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Protocol, Sequence

from app.internal.persona.enums import PersonaModifier, PersonaType
from app.internal.persona.transition_buffer_models import PersonaTransitionEvaluation, TransitionCandidate
from app.internal.persona.transition_buffer_repository import PersonaTransitionBufferStore


@dataclass(frozen=True, slots=True)
class TransitionReason:
    """Structured reason payload for transition recommendation/decision."""

    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class PersonaTransitionDecision:
    """Transition recommendation and final decision for downstream orchestration."""

    session_id: str
    current_persona: PersonaType
    candidate_persona: PersonaType
    recommendation_allowed: bool
    transition_allowed: bool
    score_ratio: float
    required_ratio_recommendation: float
    required_ratio_final: float
    stability_window: int
    stable_evidence_count: int
    modifiers: tuple[PersonaModifier, ...]
    reasons: tuple[TransitionReason, ...]
    decided_at: datetime


class PersonaTransitionHistoryWriter(Protocol):
    """Persistence interface for transition history records."""

    def record_transition(self, decision: PersonaTransitionDecision) -> None:
        """Persist one transition decision in durable transition history."""


class PersonaTransitionManager:
    """Applies deterministic score and stability checks to transition personas."""

    def __init__(
        self,
        *,
        buffer_store: PersonaTransitionBufferStore,
        min_score_multiplier: float = 1.25,
        stability_window: int = 3,
        trust_low_speed_penalty: float = 0.5,
        history_writer: PersonaTransitionHistoryWriter | None = None,
    ) -> None:
        if min_score_multiplier < 1.0:
            raise ValueError("min_score_multiplier must be >= 1.0")
        if stability_window < 2:
            raise ValueError("stability_window must be >= 2")
        if trust_low_speed_penalty < 0.0 or trust_low_speed_penalty >= 1.0:
            raise ValueError("trust_low_speed_penalty must be in [0.0, 1.0)")

        self.buffer_store = buffer_store
        self.min_score_multiplier = min_score_multiplier
        self.stability_window = stability_window
        self.trust_low_speed_penalty = trust_low_speed_penalty
        self.history_writer = history_writer

    async def evaluate_transition(
        self,
        *,
        session_id: str,
        current_persona: PersonaType,
        candidate_persona: PersonaType,
        persona_scores: Mapping[PersonaType, float],
        confidence: float,
        modifiers: Sequence[PersonaModifier] = (),
        signal_summary: Mapping[str, float] | None = None,
        source: str = "transition_manager",
    ) -> PersonaTransitionDecision:
        """Evaluate transition recommendation and final approval for one message step."""

        current_score = float(persona_scores.get(current_persona, 0.0))
        candidate_score = float(persona_scores.get(candidate_persona, 0.0))
        score_ratio = self._score_ratio(candidate_score, current_score)

        evaluation = PersonaTransitionEvaluation(
            persona_type=candidate_persona if candidate_score >= current_score else current_persona,
            confidence=confidence,
            persona_scores={persona: float(score) for persona, score in persona_scores.items()},
            signal_summary=dict(signal_summary or {}),
            source=source,
        )
        buffer = await self.buffer_store.append_evaluation(session_id, evaluation)

        effective_multiplier = self.min_score_multiplier
        modifier_set = tuple(modifiers)
        if PersonaModifier.TRUST_LOW in modifier_set:
            effective_multiplier = self.min_score_multiplier * (1.0 + self.trust_low_speed_penalty)

        stable_recommendation, stable_count = self._has_stable_evidence(
            evaluations=buffer.evaluations,
            current_persona=current_persona,
            candidate_persona=candidate_persona,
            required_ratio=self.min_score_multiplier,
        )
        recommendation_allowed = (score_ratio >= self.min_score_multiplier) and stable_recommendation

        stable_final, _ = self._has_stable_evidence(
            evaluations=buffer.evaluations,
            current_persona=current_persona,
            candidate_persona=candidate_persona,
            required_ratio=effective_multiplier,
        )
        transition_allowed = (score_ratio >= effective_multiplier) and stable_final

        reasons = self._build_reasons(
            score_ratio=score_ratio,
            recommendation_allowed=recommendation_allowed,
            transition_allowed=transition_allowed,
            stable_evidence_count=stable_count,
            effective_multiplier=effective_multiplier,
            modifiers=modifier_set,
        )

        if recommendation_allowed:
            await self.buffer_store.set_transition_candidate(
                session_id,
                TransitionCandidate(
                    candidate_persona=candidate_persona,
                    support=min(1.0, score_ratio / max(self.min_score_multiplier, 1e-6)),
                    reason="stable candidate evidence",
                    observed_at=datetime.now(timezone.utc),
                ),
            )
        else:
            await self.buffer_store.clear_transition_candidate(session_id)

        decision = PersonaTransitionDecision(
            session_id=session_id,
            current_persona=current_persona,
            candidate_persona=candidate_persona,
            recommendation_allowed=recommendation_allowed,
            transition_allowed=transition_allowed,
            score_ratio=score_ratio,
            required_ratio_recommendation=self.min_score_multiplier,
            required_ratio_final=effective_multiplier,
            stability_window=self.stability_window,
            stable_evidence_count=stable_count,
            modifiers=modifier_set,
            reasons=reasons,
            decided_at=datetime.now(timezone.utc),
        )

        if self.history_writer is not None:
            self.history_writer.record_transition(decision)

        return decision

    def _has_stable_evidence(
        self,
        *,
        evaluations: Sequence[PersonaTransitionEvaluation],
        current_persona: PersonaType,
        candidate_persona: PersonaType,
        required_ratio: float,
    ) -> tuple[bool, int]:
        if len(evaluations) < self.stability_window:
            return False, 0

        window = evaluations[-self.stability_window :]
        stable_count = 0
        for item in window:
            if item.persona_type is not candidate_persona:
                continue

            candidate_score = float(item.persona_scores.get(candidate_persona, 0.0))
            current_score = float(item.persona_scores.get(current_persona, 0.0))
            if self._score_ratio(candidate_score, current_score) >= required_ratio:
                stable_count += 1

        return stable_count == self.stability_window, stable_count

    @staticmethod
    def _score_ratio(candidate_score: float, current_score: float) -> float:
        if candidate_score <= 0.0:
            return 0.0
        if current_score <= 0.0:
            return float("inf")
        return candidate_score / current_score

    def _build_reasons(
        self,
        *,
        score_ratio: float,
        recommendation_allowed: bool,
        transition_allowed: bool,
        stable_evidence_count: int,
        effective_multiplier: float,
        modifiers: Sequence[PersonaModifier],
    ) -> tuple[TransitionReason, ...]:
        reasons: list[TransitionReason] = []

        if score_ratio < self.min_score_multiplier:
            reasons.append(
                TransitionReason(
                    code="score_ratio_too_low",
                    detail=f"ratio={score_ratio:.3f} required={self.min_score_multiplier:.3f}",
                )
            )

        if stable_evidence_count < self.stability_window:
            reasons.append(
                TransitionReason(
                    code="insufficient_stability",
                    detail=f"stable_count={stable_evidence_count} required={self.stability_window}",
                )
            )

        if PersonaModifier.TRUST_LOW in modifiers:
            reasons.append(
                TransitionReason(
                    code="trust_low_penalty",
                    detail=f"effective_multiplier={effective_multiplier:.3f}",
                )
            )

        if recommendation_allowed and not transition_allowed:
            reasons.append(
                TransitionReason(
                    code="recommendation_only",
                    detail="candidate recommended but blocked by final threshold",
                )
            )

        if transition_allowed:
            reasons.append(
                TransitionReason(
                    code="transition_approved",
                    detail="candidate passed ratio and stability checks",
                )
            )

        return tuple(reasons)
