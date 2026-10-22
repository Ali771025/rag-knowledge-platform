"""Typed models for structured observability logging."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID

from app.observability.exceptions import ObservabilityContractError


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _validate_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ObservabilityContractError(f"`{field_name}` must be a non-empty string.")
    return normalized


def _validate_optional_non_empty(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ObservabilityContractError(f"`{field_name}` cannot be blank when provided.")
    return normalized


class StructuredLogLevel(StrEnum):
    """Supported structured log severity levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredLogCategory(StrEnum):
    """Supported observability log categories."""

    CONVERSATION = "conversation"
    INTENT = "intent"
    REQUEST = "request"
    ERROR = "error"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class StructuredLogEvent:
    """Transport-agnostic structured log payload."""

    message: str
    level: StructuredLogLevel = StructuredLogLevel.INFO
    category: StructuredLogCategory = StructuredLogCategory.SYSTEM
    service: str = "ragai-backend"
    trace_id: str | None = None
    user_id: UUID | str | None = None
    endpoint: str | None = None
    state: str | None = None
    duration_ms: float | None = None
    tokens: int | Mapping[str, int] | None = None
    cost_usd: Decimal | float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        object.__setattr__(self, "message", _validate_non_empty(self.message, "message"))
        object.__setattr__(self, "service", _validate_non_empty(self.service, "service"))
        object.__setattr__(self, "trace_id", _validate_optional_non_empty(self.trace_id, "trace_id"))
        object.__setattr__(self, "endpoint", _validate_optional_non_empty(self.endpoint, "endpoint"))
        object.__setattr__(self, "state", _validate_optional_non_empty(self.state, "state"))

        if self.timestamp.tzinfo is None:
            raise ObservabilityContractError("`timestamp` must be timezone-aware.")

        if self.duration_ms is not None and self.duration_ms < 0:
            raise ObservabilityContractError("`duration_ms` cannot be negative.")

        if isinstance(self.tokens, int) and self.tokens < 0:
            raise ObservabilityContractError("`tokens` cannot be negative.")

        if isinstance(self.tokens, Mapping):
            for key, value in self.tokens.items():
                _validate_non_empty(str(key), "tokens.key")
                if int(value) < 0:
                    raise ObservabilityContractError("`tokens` mapping values cannot be negative.")

        if self.cost_usd is not None and Decimal(str(self.cost_usd)) < Decimal("0"):
            raise ObservabilityContractError("`cost_usd` cannot be negative.")

        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))
