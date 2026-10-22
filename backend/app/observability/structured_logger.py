"""Structured JSON logging foundation for observability events."""

from __future__ import annotations

import json
import logging
import os
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Mapping, Sequence

from app.observability.logging_models import (
    StructuredLogCategory,
    StructuredLogEvent,
    StructuredLogLevel,
)

_DEFAULT_REDACTED = "[REDACTED]"
_DEFAULT_SENSITIVE_FIELDS = {
    "password",
    "secret",
    "token",
    "api_key",
    "authorization",
    "access_token",
    "refresh_token",
    "ssn",
    "credit_card",
}
_DEFAULT_SENSITIVE_VALUE_KEYS = {
    "password",
    "secret",
    "token",
    "api_key",
    "authorization",
    "access_token",
    "refresh_token",
}


@dataclass(frozen=True, slots=True)
class RedactionConfig:
    """Redaction configuration for structured logger sanitization."""

    sensitive_fields: frozenset[str] = field(default_factory=lambda: frozenset(_DEFAULT_SENSITIVE_FIELDS))
    sensitive_value_keys: frozenset[str] = field(default_factory=lambda: frozenset(_DEFAULT_SENSITIVE_VALUE_KEYS))
    redacted_value: str = _DEFAULT_REDACTED


class StructuredLogger:
    """JSON logger wrapper with sanitization and bounded event shape.

    Design goals:
    - stdout-first for containers
    - thread-safe through stdlib logging internals
    - async-safe by avoiding mutable shared payload state
    - framework-agnostic event contracts
    """

    def __init__(
        self,
        *,
        service: str = "ragai-backend",
        logger_name: str = "app.structured",
        level: str | int = logging.INFO,
        redaction: RedactionConfig | None = None,
    ) -> None:
        self.service = service
        self.redaction = redaction or RedactionConfig()
        self._logger = logging.getLogger(logger_name)

        if isinstance(level, str):
            resolved_level = logging.getLevelName(level.upper())
            if not isinstance(resolved_level, int):
                resolved_level = logging.INFO
            level = resolved_level

        self._logger.setLevel(level)
        self._logger.propagate = False

        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(level)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)

    def emit(self, event: StructuredLogEvent, *, exc_info: BaseException | None = None) -> None:
        """Emit one structured event as a JSON log line."""

        payload = self._build_payload(event=event, exc_info=exc_info)
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=self._json_default)

        level_method = {
            StructuredLogLevel.DEBUG: self._logger.debug,
            StructuredLogLevel.INFO: self._logger.info,
            StructuredLogLevel.WARNING: self._logger.warning,
            StructuredLogLevel.ERROR: self._logger.error,
            StructuredLogLevel.CRITICAL: self._logger.critical,
        }[event.level]
        level_method(encoded)

    def debug(self, message: str, **kwargs: Any) -> None:
        self.emit(self._event_from_level(StructuredLogLevel.DEBUG, message, **kwargs))

    def info(self, message: str, **kwargs: Any) -> None:
        self.emit(self._event_from_level(StructuredLogLevel.INFO, message, **kwargs))

    def warning(self, message: str, **kwargs: Any) -> None:
        self.emit(self._event_from_level(StructuredLogLevel.WARNING, message, **kwargs))

    def error(self, message: str, **kwargs: Any) -> None:
        self.emit(self._event_from_level(StructuredLogLevel.ERROR, message, **kwargs))

    def critical(self, message: str, **kwargs: Any) -> None:
        self.emit(self._event_from_level(StructuredLogLevel.CRITICAL, message, **kwargs))

    def _event_from_level(self, level: StructuredLogLevel, message: str, **kwargs: Any) -> StructuredLogEvent:
        return StructuredLogEvent(
            level=level,
            message=message,
            service=self.service,
            category=kwargs.pop("category", StructuredLogCategory.SYSTEM),
            trace_id=kwargs.pop("trace_id", None),
            user_id=kwargs.pop("user_id", None),
            endpoint=kwargs.pop("endpoint", None),
            state=kwargs.pop("state", None),
            duration_ms=kwargs.pop("duration_ms", None),
            tokens=kwargs.pop("tokens", None),
            cost_usd=kwargs.pop("cost_usd", None),
            metadata=kwargs.pop("metadata", {}),
        )

    def _build_payload(self, *, event: StructuredLogEvent, exc_info: BaseException | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "timestamp": event.timestamp.astimezone(UTC).isoformat(),
            "level": event.level.value,
            "service": event.service,
            "category": event.category.value,
            "trace_id": event.trace_id,
            "user_id": str(event.user_id) if event.user_id is not None else None,
            "endpoint": event.endpoint,
            "state": event.state,
            "message": event.message,
            "duration_ms": event.duration_ms,
            "tokens": self._sanitize_value(event.tokens),
            "cost_usd": self._normalize_cost(event.cost_usd),
            "metadata": self._sanitize_mapping(event.metadata),
        }

        if exc_info is not None:
            payload["error"] = {
                "type": type(exc_info).__name__,
                "message": str(exc_info),
                "stack_trace": traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__),
            }

        return payload

    def _sanitize_mapping(self, mapping: Mapping[str, Any] | None) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in dict(mapping or {}).items():
            lower_key = str(key).lower()
            if lower_key in self.redaction.sensitive_fields:
                clean[str(key)] = self.redaction.redacted_value
                continue
            clean[str(key)] = self._sanitize_value(value)
        return clean

    def _sanitize_sequence(self, values: Sequence[Any]) -> list[Any]:
        return [self._sanitize_value(value) for value in values]

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return self._sanitize_mapping(value)
        if isinstance(value, (list, tuple)):
            return self._sanitize_sequence(value)
        if isinstance(value, str):
            return self._sanitize_string_value(value)
        return value

    def _sanitize_string_value(self, value: str) -> str:
        lower = value.lower()
        for marker in self.redaction.sensitive_value_keys:
            if marker in lower:
                return self.redaction.redacted_value
        return value

    def _normalize_cost(self, cost_value: Decimal | float | None) -> float | None:
        if cost_value is None:
            return None
        return float(Decimal(str(cost_value)))

    def _json_default(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.astimezone(UTC).isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, set):
            return list(value)
        return str(value)


def get_structured_logger(
    *,
    service: str | None = None,
    logger_name: str = "app.structured",
) -> StructuredLogger:
    """Build a structured logger using environment-level defaults."""

    configured_service = service or os.getenv("SERVICE_NAME", "ragai-backend")
    level = os.getenv("STRUCTURED_LOG_LEVEL", "INFO")
    return StructuredLogger(service=configured_service, logger_name=logger_name, level=level)
