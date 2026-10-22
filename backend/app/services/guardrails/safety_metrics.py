"""Lightweight safety metrics adapter for guardrails."""

from __future__ import annotations

from typing import Callable


class SafetyMetrics:
    """Non-blocking metrics facade with safe fallback behavior."""

    def __init__(self) -> None:
        self._increment_metric = self._resolve_incrementer()

    def record_hallucination_detection(self) -> None:
        self._increment("hallucination_rate")
        self._increment("guardrails_hallucination_detection_total")

    def record_off_topic_request(self) -> None:
        self._increment("off_topic_requests_total")
        self._increment("guardrails_off_topic_requests_total")

    def record_prompt_injection_attempt(self, risk_level: str | None = None) -> None:
        self._increment("prompt_injection_attempts")
        self._increment("guardrails_prompt_injection_attempts_total")
        if risk_level:
            normalized = risk_level.strip().lower()
            if normalized in {"low", "medium", "high", "critical"}:
                self._increment(f"guardrails_prompt_injection_{normalized}_total")

    def record_low_confidence_event(self) -> None:
        self._increment("low_confidence_rate")
        self._increment("guardrails_low_confidence_total")

    def record_rejected_response(self) -> None:
        self._increment("guardrails_rejected_response_total")
        self._increment("unsafe_requests_total")

    def record_fallback_response(self) -> None:
        self._increment("fallback_response_rate")
        self._increment("guardrails_fallback_response_total")

    def record_unsafe_request(self) -> None:
        self._increment("unsafe_requests_total")
        self._increment("guardrails_unsafe_requests_total")

    def _increment(self, metric_name: str, value: int = 1) -> None:
        try:
            if self._increment_metric is not None:
                self._increment_metric(metric_name, value)
        except Exception:
            # Metrics are best-effort and must never break user flow.
            return

    def _resolve_incrementer(self) -> Callable[[str, int], None] | None:
        try:
            from app.core.monitoring import increment_metric

            return increment_metric
        except Exception:
            return None
