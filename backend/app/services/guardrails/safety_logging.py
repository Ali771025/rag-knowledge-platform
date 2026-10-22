"""Resilient structured logging adapter for guardrails safety events."""

from __future__ import annotations

import logging
from typing import Any

from app.services.guardrails.constants import UNSAFE_OUTPUT_PATTERNS

_MAX_TEXT_LENGTH = 320


class SafetyLogger:
    """Optional safety logger wrapper that never breaks request flow."""

    def __init__(self) -> None:
        self._fallback_logger = logging.getLogger("app.guardrails.safety")
        self._structured_logger = self._build_structured_logger()

    def log_off_topic(
        self,
        *,
        query: str | None = None,
        detected_topic: str | None = None,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._emit(
            level="warning",
            event_name="guardrails_off_topic",
            metadata={
                "query": query,
                "detected_topic": detected_topic,
                "confidence": confidence,
                **dict(metadata or {}),
            },
        )

    def log_prompt_injection(
        self,
        *,
        query: str | None = None,
        risk_level: str | None = None,
        matched_patterns: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._emit(
            level="warning",
            event_name="guardrails_prompt_injection",
            metadata={
                "query": query,
                "risk_level": risk_level,
                "matched_patterns": matched_patterns or [],
                **dict(metadata or {}),
            },
        )

    def log_retrieval_rejected(
        self,
        *,
        query: str | None = None,
        reason: str | None = None,
        confidence_score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._emit(
            level="info",
            event_name="guardrails_retrieval_rejected",
            metadata={
                "query": query,
                "reason": reason,
                "confidence_score": confidence_score,
                **dict(metadata or {}),
            },
        )

    def log_grounding_failed(
        self,
        *,
        response: str | None = None,
        unsupported_claims: list[str] | None = None,
        grounding_score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._emit(
            level="warning",
            event_name="guardrails_grounding_failed",
            metadata={
                "response": response,
                "unsupported_claims": unsupported_claims or [],
                "grounding_score": grounding_score,
                **dict(metadata or {}),
            },
        )

    def log_output_filtered(
        self,
        *,
        user_query: str | None = None,
        violations: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._emit(
            level="warning",
            event_name="guardrails_output_filtered",
            metadata={
                "user_query": user_query,
                "violations": violations or [],
                **dict(metadata or {}),
            },
        )

    def log_low_confidence(
        self,
        *,
        confidence_score: float | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._emit(
            level="info",
            event_name="guardrails_low_confidence",
            metadata={
                "confidence_score": confidence_score,
                "source": source,
                **dict(metadata or {}),
            },
        )

    def _emit(self, *, level: str, event_name: str, metadata: dict[str, Any]) -> None:
        safe_metadata = self._sanitize_metadata(metadata)
        try:
            if self._structured_logger is not None:
                log_method = getattr(self._structured_logger, level, self._structured_logger.info)
                log_method(
                    event_name,
                    metadata=safe_metadata,
                )
                return
        except Exception:
            # Fall through to stdlib logger and never interrupt request path.
            pass

        try:
            log_method = getattr(self._fallback_logger, level, self._fallback_logger.info)
            log_method(event_name, extra={"metadata": safe_metadata})
        except Exception:
            return

    def _sanitize_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in metadata.items():
            normalized_key = str(key).lower()
            if any(marker in normalized_key for marker in ("prompt", "policy", "developer_message")):
                sanitized[key] = "[REDACTED]"
                continue

            if isinstance(value, str):
                sanitized[key] = self._sanitize_text(value)
            elif isinstance(value, list):
                sanitized[key] = [self._sanitize_text(str(item)) for item in value[:12]]
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_metadata({str(k): v for k, v in value.items()})
            else:
                sanitized[key] = value
        return sanitized

    def _sanitize_text(self, value: str) -> str:
        lowered = value.lower()
        if any(marker in lowered for marker in UNSAFE_OUTPUT_PATTERNS):
            return "[REDACTED]"
        if len(value) <= _MAX_TEXT_LENGTH:
            return value
        return f"{value[:_MAX_TEXT_LENGTH]}..."

    def _build_structured_logger(self) -> Any | None:
        try:
            from app.observability.structured_logger import get_structured_logger

            return get_structured_logger(logger_name="app.guardrails.structured")
        except Exception:
            return None

