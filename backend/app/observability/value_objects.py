"""Transport-agnostic value objects for observability and cost monitoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID

from app.observability.exceptions import ObservabilityContractError


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


def _validate_non_negative_int(value: int, field_name: str) -> int:
    if value < 0:
        raise ObservabilityContractError(f"`{field_name}` cannot be negative.")
    return value


def _validate_non_negative_float(value: float, field_name: str) -> float:
    if value < 0:
        raise ObservabilityContractError(f"`{field_name}` cannot be negative.")
    return value


def _validate_non_negative_decimal(value: Decimal, field_name: str) -> Decimal:
    if value < Decimal("0"):
        raise ObservabilityContractError(f"`{field_name}` cannot be negative.")
    return value


def _validate_aware_datetime(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None:
        raise ObservabilityContractError(f"`{field_name}` must be timezone-aware.")
    return value


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


@dataclass(frozen=True, slots=True)
class TraceContext:
    """Cross-module correlation metadata carried with observability records."""

    trace_id: str
    span_id: str | None = None
    parent_span_id: str | None = None
    request_id: str | None = None
    session_id: UUID | None = None
    user_id: UUID | None = None
    attributes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "trace_id", _validate_non_empty(self.trace_id, "trace_id"))
        object.__setattr__(self, "span_id", _validate_optional_non_empty(self.span_id, "span_id"))
        object.__setattr__(self, "parent_span_id", _validate_optional_non_empty(self.parent_span_id, "parent_span_id"))
        object.__setattr__(self, "request_id", _validate_optional_non_empty(self.request_id, "request_id"))

        if self.span_id and self.parent_span_id and self.span_id == self.parent_span_id:
            raise ObservabilityContractError("`span_id` and `parent_span_id` cannot be identical.")

        frozen_attributes = _freeze_mapping(self.attributes)
        for key, value in frozen_attributes.items():
            _validate_non_empty(key, "attributes.key")
            _validate_non_empty(value, "attributes.value")
        object.__setattr__(self, "attributes", frozen_attributes)


@dataclass(frozen=True, slots=True)
class LatencyRecord:
    """Durations (milliseconds) collected for a single operation."""

    total_ms: float
    orchestration_ms: float | None = None
    retrieval_ms: float | None = None
    model_ms: float | None = None
    dependency_ms: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        total_ms = _validate_non_negative_float(float(self.total_ms), "total_ms")
        object.__setattr__(self, "total_ms", total_ms)

        component_sum = 0.0
        for field_name in ("orchestration_ms", "retrieval_ms", "model_ms"):
            value = getattr(self, field_name)
            if value is None:
                continue
            normalized = _validate_non_negative_float(float(value), field_name)
            component_sum += normalized
            object.__setattr__(self, field_name, normalized)

        frozen_dependency_ms = _freeze_mapping(self.dependency_ms)
        for dependency_name, latency_ms in frozen_dependency_ms.items():
            _validate_non_empty(dependency_name, "dependency_ms.key")
            component_sum += _validate_non_negative_float(float(latency_ms), "dependency_ms.value")
        object.__setattr__(self, "dependency_ms", frozen_dependency_ms)

        if component_sum > total_ms + 1e-6:
            raise ObservabilityContractError("Latency component breakdown cannot exceed `total_ms`.")


@dataclass(frozen=True, slots=True)
class TokenUsageRecord:
    """Normalized token accounting for an inference operation."""

    prompt_tokens: int
    completion_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    total_tokens: int | None = None

    def __post_init__(self) -> None:
        prompt_tokens = _validate_non_negative_int(self.prompt_tokens, "prompt_tokens")
        completion_tokens = _validate_non_negative_int(self.completion_tokens, "completion_tokens")
        cache_read_tokens = _validate_non_negative_int(self.cache_read_tokens, "cache_read_tokens")
        cache_write_tokens = _validate_non_negative_int(self.cache_write_tokens, "cache_write_tokens")

        component_total = prompt_tokens + completion_tokens + cache_read_tokens + cache_write_tokens

        if self.total_tokens is None:
            total_tokens = component_total
        else:
            total_tokens = _validate_non_negative_int(self.total_tokens, "total_tokens")
            if total_tokens < component_total:
                raise ObservabilityContractError(
                    "`total_tokens` cannot be smaller than sum(prompt/completion/cache tokens)."
                )

        object.__setattr__(self, "prompt_tokens", prompt_tokens)
        object.__setattr__(self, "completion_tokens", completion_tokens)
        object.__setattr__(self, "cache_read_tokens", cache_read_tokens)
        object.__setattr__(self, "cache_write_tokens", cache_write_tokens)
        object.__setattr__(self, "total_tokens", total_tokens)


@dataclass(frozen=True, slots=True)
class CostRecord:
    """Monetary usage accounting for a single or aggregated operation."""

    total_cost: Decimal
    currency: str = "USD"
    prompt_cost: Decimal = Decimal("0")
    completion_cost: Decimal = Decimal("0")
    cache_cost: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        currency = _validate_non_empty(self.currency, "currency").upper()
        if len(currency) != 3:
            raise ObservabilityContractError("`currency` must be a 3-letter ISO-like code.")

        total_cost = _validate_non_negative_decimal(Decimal(str(self.total_cost)), "total_cost")
        prompt_cost = _validate_non_negative_decimal(Decimal(str(self.prompt_cost)), "prompt_cost")
        completion_cost = _validate_non_negative_decimal(Decimal(str(self.completion_cost)), "completion_cost")
        cache_cost = _validate_non_negative_decimal(Decimal(str(self.cache_cost)), "cache_cost")

        if prompt_cost + completion_cost + cache_cost > total_cost + Decimal("0.000000001"):
            raise ObservabilityContractError("Cost component breakdown cannot exceed `total_cost`.")

        object.__setattr__(self, "currency", currency)
        object.__setattr__(self, "total_cost", total_cost)
        object.__setattr__(self, "prompt_cost", prompt_cost)
        object.__setattr__(self, "completion_cost", completion_cost)
        object.__setattr__(self, "cache_cost", cache_cost)
