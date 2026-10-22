"""Outbound integration contracts for observability records and alerts.

Implementations of these protocols belong outside the domain module boundary.
"""

from __future__ import annotations

from typing import Protocol

from app.observability.models import AlertEvent, DependencyHealthResult, RequestMetricsEvent, SessionRecord
from app.observability.value_objects import CostRecord, TraceContext


class RequestMetricsSink(Protocol):
    """Persists or forwards request-level metrics events."""

    def record_request_metrics(self, event: RequestMetricsEvent) -> None:
        """Record request metrics without exposing transport details."""


class SessionRecordSink(Protocol):
    """Persists or forwards session-level records."""

    def record_session(self, record: SessionRecord) -> None:
        """Record a session metrics snapshot."""


class CostRecordSink(Protocol):
    """Persists or forwards cost usage records."""

    def record_cost(self, cost: CostRecord, trace_context: TraceContext | None = None) -> None:
        """Record a cost usage event."""


class DependencyHealthSink(Protocol):
    """Persists dependency health-check results."""

    def record_dependency_health(self, result: DependencyHealthResult) -> None:
        """Record dependency health evaluation result."""


class AlertSink(Protocol):
    """Dispatches generated alerts to downstream channels."""

    def emit_alert(self, event: AlertEvent) -> None:
        """Emit an observability alert event."""
