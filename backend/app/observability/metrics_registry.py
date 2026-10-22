"""Centralized Prometheus metric definitions for observability.

Label strategy:
- keep labels bounded to a small curated set (`endpoint`, `state`, `error_type`)
- do not use raw user identifiers, trace IDs, request IDs, or free-form text
- prefer endpoint templates (e.g. `/api/v1/chat`) over concrete URL instances
"""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

REQUEST_LATENCY_BUCKETS_MS = (
    1.0,
    2.5,
    5.0,
    10.0,
    25.0,
    50.0,
    100.0,
    250.0,
    500.0,
    1_000.0,
    2_500.0,
    5_000.0,
    10_000.0,
)

SESSION_DURATION_BUCKETS_SECONDS = (
    1.0,
    5.0,
    15.0,
    30.0,
    60.0,
    120.0,
    300.0,
    600.0,
    1_800.0,
    3_600.0,
)


class ObservabilityMetricsRegistry:
    """Prometheus metric container used by collectors/services."""

    def __init__(self, *, registry: CollectorRegistry | None = None, namespace: str = "ragai") -> None:
        self.registry = registry or CollectorRegistry()

        self.requests_total = Counter(
            name=f"{namespace}_observability_requests_total",
            documentation="Count of processed requests by endpoint and state.",
            labelnames=("endpoint", "state"),
            registry=self.registry,
        )
        self.request_latency_ms = Histogram(
            name=f"{namespace}_observability_request_latency_ms",
            documentation="Request latency distribution in milliseconds by endpoint and state.",
            labelnames=("endpoint", "state"),
            buckets=REQUEST_LATENCY_BUCKETS_MS,
            registry=self.registry,
        )
        self.tokens_total = Counter(
            name=f"{namespace}_observability_tokens_total",
            documentation="Token volume by direction (input/output) and state.",
            labelnames=("direction", "state"),
            registry=self.registry,
        )
        self.cost_usd_total = Counter(
            name=f"{namespace}_observability_cost_usd_total",
            documentation="Total inferred USD cost by state.",
            labelnames=("state",),
            registry=self.registry,
        )
        self.active_sessions = Gauge(
            name=f"{namespace}_observability_active_sessions",
            documentation="Current number of active sessions.",
            registry=self.registry,
        )
        self.state_distribution = Gauge(
            name=f"{namespace}_observability_state_distribution",
            documentation="Best-effort in-process distribution of state counts.",
            labelnames=("state",),
            registry=self.registry,
        )
        self.errors_total = Counter(
            name=f"{namespace}_observability_errors_total",
            documentation="Error count by endpoint, error type, and state.",
            labelnames=("endpoint", "error_type", "state"),
            registry=self.registry,
        )
        self.session_duration_seconds = Histogram(
            name=f"{namespace}_observability_session_duration_seconds",
            documentation="Session duration distribution in seconds.",
            buckets=SESSION_DURATION_BUCKETS_SECONDS,
            registry=self.registry,
        )


_DEFAULT_REGISTRY = ObservabilityMetricsRegistry()


def get_observability_metrics_registry() -> ObservabilityMetricsRegistry:
    """Return the default singleton metrics registry instance."""

    return _DEFAULT_REGISTRY
