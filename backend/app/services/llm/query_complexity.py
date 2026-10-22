"""Deterministic heuristic query complexity analyzer."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.llm.contracts import ComplexityResult, LLMRequest


@dataclass(slots=True)
class QueryComplexityConfig:
    """Tunable thresholds and keyword sets for complexity heuristics."""

    simple_word_threshold: int = 35
    medium_word_threshold: int = 90
    complex_word_threshold: int = 180
    high_risk_keyword_weight: float = 0.45
    multi_step_weight: float = 0.20
    analysis_weight: float = 0.15
    ambiguity_weight: float = 0.10
    structured_reasoning_weight: float = 0.10
    high_risk_keywords: set[str] = field(
        default_factory=lambda: {
            "medical",
            "diagnosis",
            "treatment",
            "prescription",
            "legal",
            "lawsuit",
            "regulation",
            "compliance",
            "financial",
            "investment",
            "tax",
            "security",
            "vulnerability",
            "exploit",
            "password",
            "credential",
            "policy",
            "privacy",
        }
    )
    multi_step_markers: set[str] = field(
        default_factory=lambda: {
            "step by step",
            "first",
            "then",
            "after that",
            "workflow",
            "roadmap",
            "plan",
            "sequence",
        }
    )
    analysis_markers: set[str] = field(
        default_factory=lambda: {
            "compare",
            "comparison",
            "analyze",
            "analysis",
            "tradeoff",
            "trade-off",
            "evaluate",
            "pros and cons",
        }
    )
    ambiguity_markers: set[str] = field(
        default_factory=lambda: {
            "maybe",
            "somehow",
            "something",
            "whatever",
            "etc",
            "not sure",
            "unclear",
        }
    )
    structured_reasoning_markers: set[str] = field(
        default_factory=lambda: {
            "json",
            "table",
            "schema",
            "matrix",
            "framework",
            "bullet points",
            "checklist",
        }
    )


class QueryComplexityAnalyzer:
    """Heuristic complexity analyzer for routing decisions."""

    def __init__(self, config: QueryComplexityConfig | None = None) -> None:
        self.config = config or QueryComplexityConfig()

    async def evaluate(self, request: LLMRequest) -> ComplexityResult:
        """Classify query complexity into simple/medium/complex/high_risk."""
        text = self._build_analysis_text(request)
        normalized = text.lower()
        words = self._word_count(normalized)
        estimated_tokens = self._estimate_tokens(words)

        risk_tags: list[str] = []
        score = 0.0

        if self._contains_any(normalized, self.config.high_risk_keywords):
            score += self.config.high_risk_keyword_weight
            risk_tags.append("safety_sensitive")
        if self._contains_any(normalized, self.config.multi_step_markers):
            score += self.config.multi_step_weight
            risk_tags.append("multi_step")
        if self._contains_any(normalized, self.config.analysis_markers):
            score += self.config.analysis_weight
            risk_tags.append("analysis")
        if self._contains_any(normalized, self.config.ambiguity_markers):
            score += self.config.ambiguity_weight
            risk_tags.append("ambiguous")
        if self._contains_any(normalized, self.config.structured_reasoning_markers):
            score += self.config.structured_reasoning_weight
            risk_tags.append("structured_reasoning")

        length_factor = self._length_factor(words)
        final_score = min(1.0, score + length_factor)
        label = self._select_label(word_count=words, base_score=final_score, risk_tags=risk_tags)
        rationale = self._build_rationale(word_count=words, score=final_score, risk_tags=risk_tags)

        return ComplexityResult(
            label=label,
            score=final_score,
            estimated_input_tokens=estimated_tokens,
            rationale=rationale,
            risk_tags=risk_tags,
        )

    @staticmethod
    def _build_analysis_text(request: LLMRequest) -> str:
        message_text = " ".join(message.content for message in request.messages)
        return f"{request.prompt} {request.system_prompt or ''} {message_text}".strip()

    @staticmethod
    def _word_count(text: str) -> int:
        return len([token for token in text.split() if token])

    @staticmethod
    def _estimate_tokens(word_count: int) -> int:
        # Deterministic coarse estimate suitable for routing-only heuristics.
        return max(1, int(word_count * 1.3))

    def _length_factor(self, word_count: int) -> float:
        if word_count <= self.config.simple_word_threshold:
            return 0.05
        if word_count <= self.config.medium_word_threshold:
            return 0.20
        if word_count <= self.config.complex_word_threshold:
            return 0.35
        return 0.50

    def _select_label(self, word_count: int, base_score: float, risk_tags: list[str]) -> str:
        if "safety_sensitive" in risk_tags:
            return "high_risk"
        if word_count > self.config.complex_word_threshold or base_score >= 0.65:
            return "complex"
        if word_count > self.config.simple_word_threshold or base_score >= 0.35:
            return "medium"
        return "simple"

    @staticmethod
    def _contains_any(text: str, markers: set[str]) -> bool:
        return any(marker in text for marker in markers)

    @staticmethod
    def _build_rationale(word_count: int, score: float, risk_tags: list[str]) -> str:
        tags = ", ".join(risk_tags) if risk_tags else "none"
        return f"word_count={word_count}; score={score:.2f}; signals={tags}"
