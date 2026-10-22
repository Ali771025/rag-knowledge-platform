"""Core safety orchestration across pre/post generation guardrail modules."""

from __future__ import annotations

import re
from typing import Iterable

from app.config.guardrails import CONFIDENCE_MIN_SCORE, CONFIDENCE_REJECT_SCORE, GROUNDING_MIN_SCORE
from app.services.guardrails.confidence_engine import (
    apply_uncertainty_disclaimer,
    calculate_confidence,
    determine_response_strategy,
)
from app.services.guardrails.constants import FALLBACK_MESSAGES, FORBIDDEN_PHASE1_REQUEST_PATTERNS
from app.services.guardrails.domain_guard import detect_off_topic
from app.services.guardrails.grounding_verifier import verify_grounding
from app.services.guardrails.models import Document, PreSafetyResult, SafetyOrchestratorResult
from app.services.guardrails.output_filter import validate_output
from app.services.guardrails.prompt_injection_detector import detect_prompt_injection
from app.services.guardrails.retrieval_validator import validate_retrieval
from app.services.guardrails.safety_logging import SafetyLogger
from app.services.guardrails.safety_metrics import SafetyMetrics
from app.services.guardrails.utils import contains_any

_PERSIAN_CHAR_RE = re.compile(r"[\u0600-\u06ff]")


class SafetyOrchestrator:
    """Deterministic orchestrator that composes all guardrail layers."""

    def __init__(
        self,
        *,
        safety_logger: SafetyLogger | None = None,
        safety_metrics: SafetyMetrics | None = None,
    ) -> None:
        self.safety_logger = safety_logger or SafetyLogger()
        self.safety_metrics = safety_metrics or SafetyMetrics()

    def pre_check_user_query(
        self,
        user_query: str,
        user_state: str | None = None,
        trace_id: str | None = None,
    ) -> PreSafetyResult:
        """Run deterministic pre-generation checks on the user query."""
        _ = user_state
        try:
            injection = detect_prompt_injection(user_query)
            if injection.is_malicious:
                self.safety_logger.log_prompt_injection(
                    query=user_query,
                    risk_level=injection.risk_level,
                    matched_patterns=injection.matched_patterns,
                    metadata={"trace_id": trace_id},
                )
                self.safety_metrics.record_prompt_injection_attempt(injection.risk_level)
                self.safety_metrics.record_unsafe_request()
                self.safety_metrics.record_fallback_response()
                return PreSafetyResult(
                    is_allowed=False,
                    fallback_response=self._fallback("injection_blocked", user_query),
                    safety_flags=["prompt_injection"],
                    reason="prompt_injection_detected",
                )

            off_topic = detect_off_topic(user_query)
            if off_topic.is_off_topic:
                self.safety_logger.log_off_topic(
                    query=user_query,
                    detected_topic=off_topic.detected_topic,
                    confidence=off_topic.confidence,
                    metadata={"trace_id": trace_id},
                )
                self.safety_metrics.record_off_topic_request()
                self.safety_metrics.record_fallback_response()
                return PreSafetyResult(
                    is_allowed=False,
                    fallback_response=self._fallback("off_topic", user_query),
                    safety_flags=["off_topic"],
                    reason=off_topic.detected_topic or "off_topic",
                )

            forbidden_hits = contains_any(user_query, list(FORBIDDEN_PHASE1_REQUEST_PATTERNS))
            if forbidden_hits:
                self.safety_logger.log_output_filtered(
                    user_query=user_query,
                    violations=["forbidden_phase1_request"],
                    metadata={
                        "trace_id": trace_id,
                        "matched_patterns": forbidden_hits[:5],
                    },
                )
                self.safety_metrics.record_unsafe_request()
                self.safety_metrics.record_rejected_response()
                self.safety_metrics.record_fallback_response()
                return PreSafetyResult(
                    is_allowed=False,
                    fallback_response=self._fallback("unsafe_output", user_query),
                    safety_flags=["forbidden_phase1_request"],
                    reason="forbidden_phase1_request",
                )

            return PreSafetyResult(
                is_allowed=True,
                fallback_response=None,
                safety_flags=[],
                reason=None,
            )
        except Exception as exc:  # pragma: no cover - fail-safe path
            self.safety_logger.log_low_confidence(
                confidence_score=0.0,
                source="pre_check_error",
                metadata={"trace_id": trace_id, "error": str(exc)},
            )
            self.safety_metrics.record_low_confidence_event()
            self.safety_metrics.record_fallback_response()
            return PreSafetyResult(
                is_allowed=False,
                fallback_response=self._fallback("low_confidence", user_query),
                safety_flags=["guardrail_internal_error"],
                reason="guardrail_internal_error",
            )

    def post_check_generated_response(
        self,
        user_query: str,
        retrieved_docs: list[Document],
        llm_response: str,
        user_state: str | None = None,
        intent_score: float | None = None,
        trace_id: str | None = None,
    ) -> SafetyOrchestratorResult:
        """Run post-generation guardrails and return final safe response contract."""
        safety_flags: list[str] = []
        try:
            retrieval_result = validate_retrieval(
                query=user_query,
                retrieved_docs=retrieved_docs,
                user_state=user_state,
            )
            if not retrieval_result.is_valid:
                action = retrieval_result.fallback_action or "low_confidence"
                safety_flags.append(action)
                self.safety_logger.log_retrieval_rejected(
                    query=user_query,
                    reason=retrieval_result.reason,
                    confidence_score=retrieval_result.confidence_score,
                    metadata={"trace_id": trace_id, "fallback_action": action},
                )
                self.safety_metrics.record_low_confidence_event()
                self.safety_metrics.record_fallback_response()
                return SafetyOrchestratorResult(
                    safe_response=self._fallback(action, user_query),
                    confidence=retrieval_result.confidence_score,
                    safety_flags=self._dedupe(safety_flags),
                    fallback_used=True,
                    response_strategy="reject",
                )

            grounding = verify_grounding(llm_response, retrieved_docs)
            if not grounding.is_grounded and grounding.grounding_score < max(
                CONFIDENCE_REJECT_SCORE,
                GROUNDING_MIN_SCORE - 0.20,
            ):
                safety_flags.extend(["ungrounded_claim", "grounding_low"])
                self.safety_logger.log_grounding_failed(
                    response=llm_response,
                    unsupported_claims=grounding.unsupported_claims,
                    grounding_score=grounding.grounding_score,
                    metadata={"trace_id": trace_id},
                )
                self.safety_metrics.record_hallucination_detection()
                self.safety_metrics.record_rejected_response()
                self.safety_metrics.record_fallback_response()
                return SafetyOrchestratorResult(
                    safe_response=self._fallback("no_relevant_context", user_query),
                    confidence=grounding.grounding_score,
                    safety_flags=self._dedupe(safety_flags),
                    fallback_used=True,
                    response_strategy="reject",
                )
            if not grounding.is_grounded:
                safety_flags.append("ungrounded_claim")

            output_result = validate_output(
                user_query=user_query,
                llm_response=llm_response,
                retrieved_context=retrieved_docs,
            )
            if not output_result.is_safe:
                safety_flags.extend(["output_filtered", *output_result.violations])
                self.safety_logger.log_output_filtered(
                    user_query=user_query,
                    violations=output_result.violations,
                    metadata={"trace_id": trace_id},
                )
                self.safety_metrics.record_rejected_response()
                self.safety_metrics.record_fallback_response()
                return SafetyOrchestratorResult(
                    safe_response=output_result.filtered_response,
                    confidence=output_result.confidence_score,
                    safety_flags=self._dedupe(safety_flags),
                    fallback_used=True,
                    response_strategy="reject",
                )

            normalized_intent = self._normalize_intent_score(intent_score)
            confidence = calculate_confidence(
                retrieval_score=retrieval_result.confidence_score,
                intent_score=normalized_intent,
                grounding_score=grounding.grounding_score,
            )
            strategy = determine_response_strategy(confidence)

            final_response = llm_response
            fallback_used = False
            if strategy == "answer_with_disclaimer":
                final_response = apply_uncertainty_disclaimer(
                    llm_response,
                    language=self._detect_language(user_query, llm_response),
                )
            elif strategy == "clarify":
                safety_flags.append("low_confidence")
                fallback_used = True
                self.safety_metrics.record_low_confidence_event()
                self.safety_metrics.record_fallback_response()
                final_response = self._fallback("low_confidence", user_query)
            elif strategy == "reject":
                safety_flags.append("low_confidence")
                fallback_used = True
                self.safety_metrics.record_rejected_response()
                self.safety_metrics.record_fallback_response()
                final_response = self._fallback("no_relevant_context", user_query)

            return SafetyOrchestratorResult(
                safe_response=final_response,
                confidence=confidence,
                safety_flags=self._dedupe(safety_flags),
                fallback_used=fallback_used,
                response_strategy=strategy,
            )
        except Exception as exc:  # pragma: no cover - fail-safe path
            self.safety_logger.log_low_confidence(
                confidence_score=0.0,
                source="post_check_error",
                metadata={"trace_id": trace_id, "error": str(exc)},
            )
            self.safety_metrics.record_low_confidence_event()
            self.safety_metrics.record_fallback_response()
            return SafetyOrchestratorResult(
                safe_response=self._fallback("low_confidence", user_query),
                confidence=0.0,
                safety_flags=self._dedupe([*safety_flags, "guardrail_internal_error"]),
                fallback_used=True,
                response_strategy="reject",
            )

    def process_safe_response(
        self,
        user_query: str,
        retrieved_docs: list[Document],
        llm_response: str,
        user_state: str | None = None,
        intent_score: float | None = None,
        trace_id: str | None = None,
    ) -> SafetyOrchestratorResult:
        """Run full pre + post safety checks and return the final safe contract."""
        pre_result = self.pre_check_user_query(
            user_query=user_query,
            user_state=user_state,
            trace_id=trace_id,
        )
        if not pre_result.is_allowed:
            return SafetyOrchestratorResult(
                safe_response=pre_result.fallback_response or self._fallback("low_confidence", user_query),
                confidence=0.0,
                safety_flags=self._dedupe(pre_result.safety_flags),
                fallback_used=True,
                response_strategy="reject",
            )

        return self.post_check_generated_response(
            user_query=user_query,
            retrieved_docs=retrieved_docs,
            llm_response=llm_response,
            user_state=user_state,
            intent_score=intent_score,
            trace_id=trace_id,
        )

    def _fallback(self, key: str, reference_text: str) -> str:
        language = self._detect_language(reference_text, reference_text)
        chosen = FALLBACK_MESSAGES.get(key) or FALLBACK_MESSAGES["low_confidence"]
        return chosen.get(language, chosen.get("en", ""))

    def _detect_language(self, text_a: str, text_b: str) -> str:
        if _PERSIAN_CHAR_RE.search(f"{text_a} {text_b}"):
            return "fa"
        return "en"

    def _normalize_intent_score(self, intent_score: float | None) -> float:
        if intent_score is None:
            return CONFIDENCE_MIN_SCORE
        return max(0.0, min(1.0, float(intent_score)))

    def _dedupe(self, items: Iterable[str]) -> list[str]:
        seen: set[str] = set()
        output: list[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            output.append(item)
        return output


_DEFAULT_ORCHESTRATOR = SafetyOrchestrator()


def pre_check_user_query(
    user_query: str,
    user_state: str | None = None,
    trace_id: str | None = None,
) -> PreSafetyResult:
    """Module-level pre-check function for integration call sites."""
    return _DEFAULT_ORCHESTRATOR.pre_check_user_query(
        user_query=user_query,
        user_state=user_state,
        trace_id=trace_id,
    )


def post_check_generated_response(
    user_query: str,
    retrieved_docs: list[Document],
    llm_response: str,
    user_state: str | None = None,
    intent_score: float | None = None,
    trace_id: str | None = None,
) -> SafetyOrchestratorResult:
    """Module-level post-check function for integration call sites."""
    return _DEFAULT_ORCHESTRATOR.post_check_generated_response(
        user_query=user_query,
        retrieved_docs=retrieved_docs,
        llm_response=llm_response,
        user_state=user_state,
        intent_score=intent_score,
        trace_id=trace_id,
    )


def process_safe_response(
    user_query: str,
    retrieved_docs: list[Document],
    llm_response: str,
    user_state: str | None = None,
    intent_score: float | None = None,
    trace_id: str | None = None,
) -> SafetyOrchestratorResult:
    """Module-level full safety processing function."""
    return _DEFAULT_ORCHESTRATOR.process_safe_response(
        user_query=user_query,
        retrieved_docs=retrieved_docs,
        llm_response=llm_response,
        user_state=user_state,
        intent_score=intent_score,
        trace_id=trace_id,
    )
