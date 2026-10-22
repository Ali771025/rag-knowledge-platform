"""Enumerations used by the observability and cost monitoring domain."""

from __future__ import annotations

from enum import StrEnum


class HealthState(StrEnum):
    """High-level health status for an observed dependency."""

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class AlertType(StrEnum):
    """Semantic categories for generated observability alerts."""

    COST_THRESHOLD_BREACH = "cost_threshold_breach"
    LATENCY_SLO_BREACH = "latency_slo_breach"
    ERROR_RATE_SPIKE = "error_rate_spike"
    DEPENDENCY_UNHEALTHY = "dependency_unhealthy"
    ANOMALOUS_TRAFFIC = "anomalous_traffic"


class AlertSeverity(StrEnum):
    """Relative urgency for alert routing and handling."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class LogCategory(StrEnum):
    """Logical grouping for observability records and events."""

    REQUEST = "request"
    SESSION = "session"
    COST = "cost"
    DEPENDENCY = "dependency"
    ALERT = "alert"


class SessionState(StrEnum):
    """Lifecycle state for a tracked session snapshot."""

    STARTED = "started"
    ACTIVE = "active"
    IDLE = "idle"
    ENDED = "ended"
    ERRORED = "errored"


class DependencyType(StrEnum):
    """Normalized dependency types used in health records."""

    DATABASE = "database"
    CACHE = "cache"
    VECTOR_STORE = "vector_store"
    GRAPH_STORE = "graph_store"
    LLM_PROVIDER = "llm_provider"
    EXTERNAL_API = "external_api"
    INTERNAL_SERVICE = "internal_service"
