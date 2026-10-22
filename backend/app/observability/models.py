"""Core domain models for the observability and cost monitoring layer.

These models are framework-agnostic and transport-agnostic. They represent
internal contracts only and must remain independent from persistence wiring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.internal.conversion.policy_enums import (
    CTAOutcome,
    ConversionActionType,
    ConversionOutcome,
    EconomicSuggestionStrength,
    TriggerType,
)
from app.observability.enums import (
    AlertSeverity,
    AlertType,
    DependencyType,
    HealthState,
    LogCategory,
    SessionState,
)
from app.observability.exceptions import ObservabilityContractError
from app.observability.value_objects import CostRecord, LatencyRecord, TokenUsageRecord, TraceContext


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


def _validate_aware_datetime(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None:
        raise ObservabilityContractError(f"`{field_name}` must be timezone-aware.")
    return value


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


@dataclass(frozen=True, slots=True)
class RequestMetricsEvent:
    """Top-level request metrics event captured by this observability layer."""

    operation_name: str
    trace_context: TraceContext
    state: str
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    category: LogCategory = LogCategory.REQUEST
    status_code: int | None = None
    latency: LatencyRecord | None = None
    token_usage: TokenUsageRecord | None = None
    cost: CostRecord | None = None
    dependency_states: Mapping[str, HealthState] = field(default_factory=dict)
    tags: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation_name", _validate_non_empty(self.operation_name, "operation_name"))
        object.__setattr__(self, "state", _validate_non_empty(self.state, "state"))
        object.__setattr__(self, "occurred_at", _validate_aware_datetime(self.occurred_at, "occurred_at"))

        if self.status_code is not None and (self.status_code < 100 or self.status_code > 599):
            raise ObservabilityContractError("`status_code` must be in [100, 599] when provided.")

        frozen_dependency_states = _freeze_mapping(self.dependency_states)
        for dependency_name, dependency_state in frozen_dependency_states.items():
            _validate_non_empty(dependency_name, "dependency_states.key")
            if not isinstance(dependency_state, HealthState):
                raise ObservabilityContractError("`dependency_states` values must be `HealthState` enums.")
        object.__setattr__(self, "dependency_states", frozen_dependency_states)

        frozen_tags = _freeze_mapping(self.tags)
        for key, value in frozen_tags.items():
            _validate_non_empty(key, "tags.key")
            _validate_non_empty(value, "tags.value")
        object.__setattr__(self, "tags", frozen_tags)


@dataclass(frozen=True, slots=True)
class SessionRecord:
    """Session-level aggregate metrics record."""

    session_id: UUID
    state: SessionState
    started_at: datetime
    user_id: UUID | None = None
    ended_at: datetime | None = None
    interaction_count: int = 0
    total_tokens: int = 0
    total_cost: CostRecord = field(default_factory=lambda: CostRecord(total_cost=Decimal("0")))
    trace_context: TraceContext | None = None

    def __post_init__(self) -> None:
        started_at = _validate_aware_datetime(self.started_at, "started_at")
        object.__setattr__(self, "started_at", started_at)

        if self.ended_at is not None:
            ended_at = _validate_aware_datetime(self.ended_at, "ended_at")
            if ended_at < started_at:
                raise ObservabilityContractError("`ended_at` must be greater than or equal to `started_at`.")
            object.__setattr__(self, "ended_at", ended_at)

        object.__setattr__(self, "interaction_count", _validate_non_negative_int(self.interaction_count, "interaction_count"))
        object.__setattr__(self, "total_tokens", _validate_non_negative_int(self.total_tokens, "total_tokens"))


@dataclass(frozen=True, slots=True)
class DependencyHealthResult:
    """Health result for a monitored dependency endpoint or subsystem."""

    dependency_name: str
    dependency_type: DependencyType
    state: HealthState
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    latency_ms: float | None = None
    error_message: str | None = None
    trace_context: TraceContext | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "dependency_name", _validate_non_empty(self.dependency_name, "dependency_name"))
        object.__setattr__(self, "checked_at", _validate_aware_datetime(self.checked_at, "checked_at"))
        object.__setattr__(self, "error_message", _validate_optional_non_empty(self.error_message, "error_message"))

        if self.latency_ms is not None:
            object.__setattr__(self, "latency_ms", _validate_non_negative_float(self.latency_ms, "latency_ms"))

        if self.state is HealthState.HEALTHY and self.error_message is not None:
            raise ObservabilityContractError("`error_message` must be empty when dependency state is healthy.")

        frozen_metadata = _freeze_mapping(self.metadata)
        for key, value in frozen_metadata.items():
            _validate_non_empty(key, "metadata.key")
            _validate_non_empty(value, "metadata.value")
        object.__setattr__(self, "metadata", frozen_metadata)


@dataclass(frozen=True, slots=True)
class AnalyticsSummary:
    """Aggregation result for observability dashboards or reports."""

    window_start: datetime
    window_end: datetime
    total_requests: int
    total_errors: int
    total_tokens: int
    total_cost: CostRecord
    avg_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    state_breakdown: Mapping[str, int] = field(default_factory=dict)
    category_counts: Mapping[LogCategory, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        window_start = _validate_aware_datetime(self.window_start, "window_start")
        window_end = _validate_aware_datetime(self.window_end, "window_end")
        if window_end < window_start:
            raise ObservabilityContractError("`window_end` must be greater than or equal to `window_start`.")

        object.__setattr__(self, "window_start", window_start)
        object.__setattr__(self, "window_end", window_end)

        total_requests = _validate_non_negative_int(self.total_requests, "total_requests")
        total_errors = _validate_non_negative_int(self.total_errors, "total_errors")
        total_tokens = _validate_non_negative_int(self.total_tokens, "total_tokens")

        if total_errors > total_requests:
            raise ObservabilityContractError("`total_errors` cannot exceed `total_requests`.")

        object.__setattr__(self, "total_requests", total_requests)
        object.__setattr__(self, "total_errors", total_errors)
        object.__setattr__(self, "total_tokens", total_tokens)

        if self.avg_latency_ms is not None:
            object.__setattr__(self, "avg_latency_ms", _validate_non_negative_float(self.avg_latency_ms, "avg_latency_ms"))
        if self.p95_latency_ms is not None:
            object.__setattr__(self, "p95_latency_ms", _validate_non_negative_float(self.p95_latency_ms, "p95_latency_ms"))

        frozen_state_breakdown = _freeze_mapping(self.state_breakdown)
        for state_name, count in frozen_state_breakdown.items():
            _validate_non_empty(state_name, "state_breakdown.key")
            _validate_non_negative_int(count, "state_breakdown.value")
        object.__setattr__(self, "state_breakdown", frozen_state_breakdown)

        frozen_category_counts = _freeze_mapping(self.category_counts)
        for category, count in frozen_category_counts.items():
            if not isinstance(category, LogCategory):
                raise ObservabilityContractError("`category_counts` keys must be `LogCategory` enums.")
            _validate_non_negative_int(count, "category_counts.value")
        object.__setattr__(self, "category_counts", frozen_category_counts)


@dataclass(frozen=True, slots=True)
class AlertEvent:
    """Typed alert event produced from observability analytics signals."""

    alert_type: AlertType
    severity: AlertSeverity
    message: str
    alert_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    trace_context: TraceContext | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    is_resolved: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "message", _validate_non_empty(self.message, "message"))
        object.__setattr__(self, "created_at", _validate_aware_datetime(self.created_at, "created_at"))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


class ConversionEvent(BaseModel):
    """Conversion feedback event payload."""

    event_id: UUID = Field(default_factory=uuid4)
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    session_id: str = Field(..., min_length=1, max_length=128)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    persona: str = Field(..., min_length=1, max_length=64)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    modifiers: list[str] = Field(default_factory=list)
    stage: str = Field(..., min_length=1, max_length=64)
    trust_score: float = Field(default=0.0, ge=0.0, le=1.0)
    engagement_score: float = Field(default=0.0, ge=0.0, le=1.0)
    triggers_used: list[TriggerType] = Field(default_factory=list)
    cta_type: ConversionActionType | None = None
    cta_strength: EconomicSuggestionStrength = EconomicSuggestionStrength.NONE
    outcome: ConversionOutcome = ConversionOutcome.NO_CHANGE
    cta_outcome: CTAOutcome | None = None
    experiment_variant: str | None = Field(default=None, min_length=1, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CTAResponseEvent(BaseModel):
    """CTA response feedback event payload."""

    event_id: UUID = Field(default_factory=uuid4)
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    session_id: str = Field(..., min_length=1, max_length=128)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    persona: str = Field(..., min_length=1, max_length=64)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    modifiers: list[str] = Field(default_factory=list)
    stage: str = Field(..., min_length=1, max_length=64)
    trust_score: float = Field(default=0.0, ge=0.0, le=1.0)
    engagement_score: float = Field(default=0.0, ge=0.0, le=1.0)
    triggers_used: list[TriggerType] = Field(default_factory=list)
    cta_type: ConversionActionType | None = None
    cta_strength: EconomicSuggestionStrength = EconomicSuggestionStrength.NONE
    outcome: ConversionOutcome = ConversionOutcome.NO_CHANGE
    cta_outcome: CTAOutcome
    blocked_reason: str | None = Field(default=None, min_length=1, max_length=255)
    experiment_variant: str | None = Field(default=None, min_length=1, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TriggerEvent(BaseModel):
    """Trigger-level feedback event payload."""

    event_id: UUID = Field(default_factory=uuid4)
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    session_id: str = Field(..., min_length=1, max_length=128)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    persona: str = Field(..., min_length=1, max_length=64)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    modifiers: list[str] = Field(default_factory=list)
    stage: str = Field(..., min_length=1, max_length=64)
    trust_score: float = Field(default=0.0, ge=0.0, le=1.0)
    engagement_score: float = Field(default=0.0, ge=0.0, le=1.0)
    triggers_used: list[TriggerType] = Field(default_factory=list)
    cta_type: ConversionActionType | None = None
    cta_strength: EconomicSuggestionStrength = EconomicSuggestionStrength.NONE
    outcome: ConversionOutcome = ConversionOutcome.NO_CHANGE
    cta_outcome: CTAOutcome | None = None
    experiment_variant: str | None = Field(default=None, min_length=1, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FunnelOutcomeEvent(BaseModel):
    """Funnel stage/outcome feedback event payload."""

    event_id: UUID = Field(default_factory=uuid4)
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    session_id: str = Field(..., min_length=1, max_length=128)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    persona: str = Field(..., min_length=1, max_length=64)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    modifiers: list[str] = Field(default_factory=list)
    stage: str = Field(..., min_length=1, max_length=64)
    trust_score: float = Field(default=0.0, ge=0.0, le=1.0)
    engagement_score: float = Field(default=0.0, ge=0.0, le=1.0)
    triggers_used: list[TriggerType] = Field(default_factory=list)
    cta_type: ConversionActionType | None = None
    cta_strength: EconomicSuggestionStrength = EconomicSuggestionStrength.NONE
    outcome: ConversionOutcome
    cta_outcome: CTAOutcome | None = None
    experiment_variant: str | None = Field(default=None, min_length=1, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
