"""Stateless heuristics for detecting user knowledge level.

Heuristic summary:
- Assessment-based detection converts numeric and textual signals into a score.
- Query-based detection evaluates terminology complexity, intent depth, and specificity.
- Higher scores map to progressively more advanced knowledge levels.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.models.user_profile import KnowledgeLevel


class KnowledgeDetector:
    """Detects knowledge level using deterministic, rule-based heuristics."""

    _ADVANCED_TERMS = {
        "latency",
        "throughput",
        "vector",
        "embedding",
        "normalization",
        "tokenization",
        "concurrency",
        "asynchronous",
        "transaction",
        "architecture",
        "optimization",
        "serialization",
    }
    _BEGINNER_INTENTS = {
        "what is",
        "new to",
        "beginner",
        "start with",
        "explain simply",
    }
    _DEEP_INTENTS = {
        "tradeoff",
        "trade-off",
        "benchmark",
        "optimize",
        "scalability",
        "failure mode",
        "consistency",
        "why does",
        "under what",
    }

    def detect_from_assessment(self, answers: dict[str, Any]) -> KnowledgeLevel:
        """Infer knowledge level from assessment answers using additive scoring.

        Scoring logic:
        - Numeric answers contribute directly after normalization.
        - Text answers contribute via beginner/advanced intent and terminology signals.
        """
        if not answers:
            return KnowledgeLevel.BEGINNER

        score = 0.0
        numeric_points = 0.0
        numeric_count = 0

        for value in answers.values():
            if isinstance(value, bool):
                numeric_points += 1.0 if value else 0.0
                numeric_count += 1
                continue
            if isinstance(value, (int, float)):
                numeric_points += self._normalize_numeric_score(float(value))
                numeric_count += 1
                continue
            if isinstance(value, str):
                score += self._score_text(value)
                continue
            if isinstance(value, list):
                score += sum(self._score_text(str(item)) for item in value)
                continue
            if isinstance(value, Mapping):
                score += sum(self._score_text(str(item)) for item in value.values())

        if numeric_count:
            score += (numeric_points / numeric_count) * 4.0

        return self._score_to_level(score)

    def detect_from_query(self, user_message: str) -> KnowledgeLevel:
        """Infer knowledge level from a single query with deterministic heuristics.

        Heuristics:
        - Terminology complexity: counts domain-specific technical terms.
        - Specificity: rewards concrete constraints, versions, and code-like tokens.
        - Intent depth: rewards comparative/causal and systems-oriented questions.
        """
        text = user_message.strip().lower()
        if not text:
            return KnowledgeLevel.BEGINNER

        score = self._score_text(text)

        if any(intent in text for intent in self._DEEP_INTENTS):
            score += 2.0
        if any(intent in text for intent in self._BEGINNER_INTENTS):
            score -= 1.5
        if any(char.isdigit() for char in text):
            score += 0.8
        if any(token in text for token in ("->", "::", "()", "api", "sql", "json", "http")):
            score += 1.0
        if len(text.split()) >= 20:
            score += 0.6

        return self._score_to_level(score)

    def detect_confidence(self, score: float) -> float:
        """Return a normalized confidence in [0.0, 1.0] from heuristic score."""
        clamped = max(0.0, min(12.0, score))
        return round(clamped / 12.0, 3)

    def _score_text(self, text: str) -> float:
        words = [word.strip(".,!?;:()[]{}'\"") for word in text.lower().split()]
        advanced_hits = sum(1 for word in words if word in self._ADVANCED_TERMS)
        long_word_hits = sum(1 for word in words if len(word) >= 10)
        depth_hits = sum(1 for phrase in self._DEEP_INTENTS if phrase in text.lower())
        return (advanced_hits * 0.9) + (long_word_hits * 0.2) + (depth_hits * 0.4)

    def _normalize_numeric_score(self, value: float) -> float:
        if value <= 1:
            return 0.0
        if value <= 5:
            return (value - 1.0) / 4.0
        if value <= 10:
            return value / 10.0
        return min(value / 100.0, 1.0)

    def _score_to_level(self, score: float) -> KnowledgeLevel:
        if score >= 7.0:
            return KnowledgeLevel.ADVANCED
        if score >= 3.5:
            return KnowledgeLevel.INTERMEDIATE
        return KnowledgeLevel.BEGINNER
