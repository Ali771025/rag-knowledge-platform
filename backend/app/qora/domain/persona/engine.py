from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from app.qora.config import QoraPolicyConfig, load_qora_policy
from app.qora.domain.contracts import PersonaDecision, SignalCandidate
from app.qora.domain.enums import PersonaCore, SignalSourceType
from app.qora.domain.persona.confidence import ConfidenceEngine, ConfidenceInputs
from app.qora.domain.signals.taxonomy import SIGNAL_TAXONOMY


@dataclass(frozen=True, slots=True)
class ScoreContribution:
    signal_code: str
    persona: PersonaCore
    source_weight: float
    taxonomy_weight: float
    strength: float
    contribution: float


@dataclass(frozen=True, slots=True)
class ScoringExplanation:
    decision: PersonaDecision
    contributions: tuple[ScoreContribution, ...]
    contradiction_count: int


class PersonaScoringEngine:
    def __init__(self, policy: QoraPolicyConfig | None = None) -> None:
        self.policy = policy or load_qora_policy()
        self.confidence_engine = ConfidenceEngine(self.policy)

    def evaluate(
        self,
        *,
        previous_scores: Mapping[str | PersonaCore, float],
        signals: Sequence[SignalCandidate],
        history_length: int,
        ambiguity_score: float = 0.0,
    ) -> ScoringExplanation:
        config = self.policy.scoring
        raw = {
            persona: max(0.0, float(previous_scores.get(persona, previous_scores.get(persona.value, 0.0))))
            * config.decay
            for persona in PersonaCore
        }
        contributions: list[ScoreContribution] = []
        aligned_counts = {persona: 0 for persona in PersonaCore}
        persona_strength = {persona: 0.0 for persona in PersonaCore}

        for signal in signals:
            definition = SIGNAL_TAXONOMY.get(signal.code)
            if definition is None or definition.persona is None:
                continue
            persona = definition.persona
            source_weight = (
                config.textual_weight
                if signal.source in {SignalSourceType.USER_TEXT, SignalSourceType.LLM_EXTRACTION}
                else config.behavioral_weight
            )
            taxonomy_weight = float(self.policy.signal_weights.get(signal.code, 0.0))
            contribution = signal.strength * source_weight * taxonomy_weight
            raw[persona] += contribution
            aligned_counts[persona] += 1
            persona_strength[persona] += signal.strength
            contributions.append(
                ScoreContribution(signal.code, persona, source_weight, taxonomy_weight, signal.strength, contribution)
            )

        active_personas = [persona for persona, count in aligned_counts.items() if count]
        contradiction_count = max(0, len(active_personas) - 1)
        total_signal_strength = sum(persona_strength.values()) or 1.0
        for persona in PersonaCore:
            if aligned_counts[persona] >= 2:
                raw[persona] += config.consistency_bonus * (aligned_counts[persona] - 1)
            opposing_strength = total_signal_strength - persona_strength[persona]
            raw[persona] = max(
                0.0,
                raw[persona] - config.contradiction_penalty * contradiction_count * opposing_strength / total_signal_strength,
            )

        total = sum(raw.values())
        normalized = {persona: (raw[persona] / total if total > 0.0 else 0.0) for persona in PersonaCore}
        ranked = sorted(normalized.items(), key=lambda item: item[1], reverse=True)
        top_persona, top_score = ranked[0]
        second_score = ranked[1][1]
        targeted_count = sum(aligned_counts.values())
        confidence = self.confidence_engine.calculate(
            ConfidenceInputs(
                signal_count=targeted_count,
                signal_alignment=(aligned_counts[top_persona] / targeted_count if targeted_count else 0.0),
                behavior_consistency=1.0 - min(1.0, contradiction_count / 3.0),
                cross_channel_count=len({signal.source for signal in signals}),
                intent_clarity=1.0 - ambiguity_score,
                top_score_margin=max(0.0, top_score - second_score),
                contradiction_count=contradiction_count,
                history_length=history_length,
            )
        )
        low_confidence = (
            confidence < config.confidence_threshold
            or top_score - second_score < config.top_margin_threshold
            or history_length < config.minimum_transition_evidence
        )
        decision = PersonaDecision(
            persona_core=None if low_confidence else top_persona,
            scores=normalized,
            confidence=confidence,
            evidence=[item.signal_code for item in contributions if item.persona == top_persona],
            needs_reassessment=low_confidence or contradiction_count > 0,
            discovery_oriented=low_confidence,
            candidate_personas=[persona for persona, _ in ranked[:2]] if low_confidence else [top_persona],
        )
        return ScoringExplanation(decision, tuple(contributions), contradiction_count)

