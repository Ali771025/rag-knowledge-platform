from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.qora.config import QoraPolicyConfig, load_qora_policy
from app.qora.domain.enums import PersonaCore


@dataclass(frozen=True, slots=True)
class ReassessmentDecision:
    previous_persona: PersonaCore | None
    candidate_persona: PersonaCore | None
    selected_persona: PersonaCore | None
    transition_allowed: bool
    reason: str


class PersonaReassessmentEngine:
    def __init__(self, policy: QoraPolicyConfig | None = None) -> None:
        self.policy = policy or load_qora_policy()

    def evaluate(
        self,
        *,
        current_persona: PersonaCore | None,
        candidate_persona: PersonaCore | None,
        scores: Mapping[PersonaCore, float],
        consecutive_candidate_assessments: int,
        confidence: float,
    ) -> ReassessmentDecision:
        if candidate_persona is None:
            return ReassessmentDecision(current_persona, None, current_persona, False, "candidate_not_confident")
        if candidate_persona == current_persona:
            return ReassessmentDecision(current_persona, candidate_persona, current_persona, False, "persona_unchanged")
        if confidence < self.policy.scoring.confidence_threshold:
            return ReassessmentDecision(current_persona, candidate_persona, current_persona, False, "confidence_below_threshold")
        if consecutive_candidate_assessments < self.policy.scoring.minimum_transition_evidence:
            return ReassessmentDecision(current_persona, candidate_persona, current_persona, False, "insufficient_stable_evidence")
        current_score = float(scores.get(current_persona, 0.0)) if current_persona else 0.0
        candidate_score = float(scores.get(candidate_persona, 0.0))
        ratio = float("inf") if current_score <= 0.0 and candidate_score > 0.0 else candidate_score / max(current_score, 1e-9)
        if current_persona is not None and ratio < self.policy.scoring.transition_score_ratio:
            return ReassessmentDecision(current_persona, candidate_persona, current_persona, False, "score_ratio_below_threshold")
        return ReassessmentDecision(current_persona, candidate_persona, candidate_persona, True, "stable_evidence_confirmed")

