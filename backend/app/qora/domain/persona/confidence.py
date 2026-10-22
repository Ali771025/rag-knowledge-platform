from __future__ import annotations

from dataclasses import dataclass

from app.qora.config import QoraPolicyConfig


@dataclass(frozen=True, slots=True)
class ConfidenceInputs:
    signal_count: int
    signal_alignment: float
    behavior_consistency: float
    cross_channel_count: int
    intent_clarity: float
    top_score_margin: float
    contradiction_count: int
    history_length: int


class ConfidenceEngine:
    def __init__(self, policy: QoraPolicyConfig) -> None:
        self.weights = policy.confidence_weights

    def calculate(self, inputs: ConfidenceInputs) -> float:
        factors = {
            "signal_count": min(1.0, inputs.signal_count / 8.0),
            "signal_alignment": self._clamp(inputs.signal_alignment),
            "behavior_consistency": self._clamp(inputs.behavior_consistency),
            "cross_channel_evidence": min(1.0, inputs.cross_channel_count / 3.0),
            "intent_clarity": self._clamp(inputs.intent_clarity),
            "top_score_margin": min(1.0, max(0.0, inputs.top_score_margin) / 0.5),
            "contradiction_count": 1.0 - min(1.0, inputs.contradiction_count / 4.0),
            "history_length": min(1.0, inputs.history_length / 10.0),
        }
        weight_total = sum(max(0.0, weight) for weight in self.weights.values()) or 1.0
        score = sum(factors.get(name, 0.0) * max(0.0, weight) for name, weight in self.weights.items())
        return round(self._clamp(score / weight_total), 6)

    @staticmethod
    def _clamp(value: float) -> float:
        return min(1.0, max(0.0, float(value)))

