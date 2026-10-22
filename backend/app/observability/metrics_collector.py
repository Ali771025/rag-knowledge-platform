"""Prometheus-backed metrics collector for observability signals."""

from __future__ import annotations

import re
from threading import Lock
from uuid import UUID

from app.observability.metrics_registry import (
    ObservabilityMetricsRegistry,
    get_observability_metrics_registry,
)


class MetricsCollector:
    """Lightweight in-process metrics recorder.

    Label safety policy:
    - never emit raw user IDs as labels
    - use bounded endpoint templates and state names only
    - normalize free-form inputs into low-cardinality buckets
    """

    def __init__(self, registry: ObservabilityMetricsRegistry | None = None) -> None:
        self.registry = registry or get_observability_metrics_registry()
        self._state_counts: dict[str, int] = {}
        self._active_session_count = 0
        self._lock = Lock()
        self._path_segment_id_pattern = re.compile(r"/[0-9a-fA-F-]{8,}(?=/|$)")

    def record_request(self, endpoint: str, user_id: UUID | None, state: str) -> None:
        """Record request volume by endpoint/state.

        `user_id` is accepted for interface compatibility, but intentionally not used
        as a label to avoid high-cardinality time series explosion.
        """

        del user_id
        endpoint_label = self._normalize_endpoint(endpoint)
        state_label = self._normalize_state(state)
        self.registry.requests_total.labels(endpoint=endpoint_label, state=state_label).inc()
        self._adjust_state_count(state_label, 1)

    def record_latency(self, endpoint: str, duration_ms: float, state: str | None = None) -> None:
        endpoint_label = self._normalize_endpoint(endpoint)
        state_label = self._normalize_state(state)
        safe_duration_ms = max(0.0, float(duration_ms))
        self.registry.request_latency_ms.labels(endpoint=endpoint_label, state=state_label).observe(safe_duration_ms)

    def record_tokens(
        self,
        input_tokens: int,
        output_tokens: int,
        user_id: UUID | None = None,
        state: str | None = None,
    ) -> None:
        """Record token usage totals without user-level labels."""

        del user_id
        state_label = self._normalize_state(state)
        if input_tokens > 0:
            self.registry.tokens_total.labels(direction="input", state=state_label).inc(float(input_tokens))
        if output_tokens > 0:
            self.registry.tokens_total.labels(direction="output", state=state_label).inc(float(output_tokens))

    def record_cost(self, cost_usd: float, user_id: UUID | None = None, state: str | None = None) -> None:
        """Record normalized USD cost without user-level labels."""

        del user_id
        normalized_cost = max(0.0, float(cost_usd))
        if normalized_cost == 0.0:
            return
        state_label = self._normalize_state(state)
        self.registry.cost_usd_total.labels(state=state_label).inc(normalized_cost)

    def record_error(self, endpoint: str, error_type: str, state: str | None = None) -> None:
        endpoint_label = self._normalize_endpoint(endpoint)
        error_type_label = self._normalize_error_type(error_type)
        state_label = self._normalize_state(state)
        self.registry.errors_total.labels(
            endpoint=endpoint_label,
            error_type=error_type_label,
            state=state_label,
        ).inc()

    def record_session_start(self, user_id: UUID | None) -> None:
        """Increment active session gauge (user is intentionally not a label)."""

        del user_id
        with self._lock:
            self._active_session_count += 1
            self.registry.active_sessions.set(self._active_session_count)

    def record_session_end(self, user_id: UUID | None, duration_seconds: float) -> None:
        """Decrement active session gauge and observe bounded duration."""

        del user_id
        safe_duration = max(0.0, float(duration_seconds))

        with self._lock:
            self._active_session_count = max(0, self._active_session_count - 1)
            self.registry.active_sessions.set(self._active_session_count)

        self.registry.session_duration_seconds.observe(safe_duration)

    def record_state_transition(self, from_state: str, to_state: str, user_id: UUID | None) -> None:
        """Track coarse-grained state distribution changes.

        `user_id` is ignored intentionally for low-cardinality Prometheus usage.
        """

        del user_id
        normalized_from = self._normalize_state(from_state)
        normalized_to = self._normalize_state(to_state)

        if normalized_from == normalized_to:
            return

        self._adjust_state_count(normalized_from, -1)
        self._adjust_state_count(normalized_to, 1)

    def _adjust_state_count(self, state: str, delta: int) -> None:
        with self._lock:
            current = self._state_counts.get(state, 0)
            next_value = max(0, current + delta)
            self._state_counts[state] = next_value
            self.registry.state_distribution.labels(state=state).set(float(next_value))

    def _normalize_endpoint(self, endpoint: str) -> str:
        normalized = (endpoint or "").strip().lower()
        if not normalized:
            return "unknown"
        # Replace UUID/id-like path fragments to keep series bounded.
        normalized = self._path_segment_id_pattern.sub("/:id", normalized)
        if len(normalized) > 80:
            return normalized[:80]
        return normalized

    def _normalize_state(self, state: str | None) -> str:
        normalized = (state or "").strip().lower()
        if not normalized:
            return "unknown"
        if len(normalized) > 40:
            return normalized[:40]
        return normalized

    def _normalize_error_type(self, error_type: str) -> str:
        normalized = (error_type or "").strip().lower().replace(" ", "_")
        if not normalized:
            return "unknown"
        if len(normalized) > 60:
            return normalized[:60]
        return normalized
