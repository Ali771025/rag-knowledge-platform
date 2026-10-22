"""Lightweight Celery task metrics adapter.

This module is backend-agnostic at the service boundary and safely degrades to
no-op behavior when metrics dependencies are unavailable.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Gauge, Histogram
except Exception:  # pragma: no cover - metrics dependency is optional
    Counter = Gauge = Histogram = None  # type: ignore[assignment]

try:
    from app.observability.metrics_registry import get_observability_metrics_registry
except Exception:  # pragma: no cover - observability registry may be unavailable
    get_observability_metrics_registry = None  # type: ignore[assignment]

_UNKNOWN_LABEL = "unknown"
_LABEL_MAX_LEN = 64
_LABEL_ALLOWED_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


class _NoopTaskMetricsBackend:
    """No-op backend used when no metrics system is available."""

    def record_task_started(self, task_name: str, queue: str | None = None) -> None:
        del task_name, queue

    def record_task_success(self, task_name: str, duration_seconds: float, queue: str | None = None) -> None:
        del task_name, duration_seconds, queue

    def record_task_failure(self, task_name: str, queue: str | None = None) -> None:
        del task_name, queue

    def record_task_retry(self, task_name: str, retry_count: int, queue: str | None = None) -> None:
        del task_name, retry_count, queue

    def record_queue_size(self, queue: str, size: int) -> None:
        del queue, size


class _PrometheusTaskMetricsBackend:
    """Prometheus-backed backend bound to the project's shared registry."""

    def __init__(self) -> None:
        if Counter is None or Gauge is None or Histogram is None or get_observability_metrics_registry is None:
            raise RuntimeError("prometheus backend is unavailable")

        observability_registry = get_observability_metrics_registry()
        registry = observability_registry.registry
        self._task_total = self._get_or_create_counter(
            registry=registry,
            name="celery_task_total",
            documentation="Total number of Celery task lifecycle events by task, queue, and status.",
            labelnames=("task_name", "queue", "status"),
        )
        self._task_failures = self._get_or_create_counter(
            registry=registry,
            name="celery_task_failures",
            documentation="Total number of failed Celery tasks by task and queue.",
            labelnames=("task_name", "queue"),
        )
        self._task_retry_total = self._get_or_create_counter(
            registry=registry,
            name="celery_task_retries_total",
            documentation="Total number of Celery retry events by task and queue.",
            labelnames=("task_name", "queue"),
        )
        self._task_duration_seconds = self._get_or_create_histogram(
            registry=registry,
            name="celery_task_duration_seconds",
            documentation="Duration of successful Celery task runs in seconds.",
            labelnames=("task_name", "queue"),
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
        )
        self._queue_size = self._get_or_create_gauge(
            registry=registry,
            name="celery_queue_size",
            documentation="Best-effort current queue depth by queue name.",
            labelnames=("queue",),
        )
        if any(metric is None for metric in (self._task_total, self._task_failures, self._task_retry_total, self._task_duration_seconds, self._queue_size)):
            raise RuntimeError("failed to initialize one or more task metrics")

    def record_task_started(self, task_name: str, queue: str | None = None) -> None:
        self._task_total.labels(
            task_name=self._normalize_label(task_name),
            queue=self._normalize_label(queue),
            status="started",
        ).inc()

    def record_task_success(self, task_name: str, duration_seconds: float, queue: str | None = None) -> None:
        safe_duration = max(0.0, float(duration_seconds))
        task_label = self._normalize_label(task_name)
        queue_label = self._normalize_label(queue)
        self._task_total.labels(task_name=task_label, queue=queue_label, status="success").inc()
        self._task_duration_seconds.labels(task_name=task_label, queue=queue_label).observe(safe_duration)

    def record_task_failure(self, task_name: str, queue: str | None = None) -> None:
        task_label = self._normalize_label(task_name)
        queue_label = self._normalize_label(queue)
        self._task_total.labels(task_name=task_label, queue=queue_label, status="failure").inc()
        self._task_failures.labels(task_name=task_label, queue=queue_label).inc()

    def record_task_retry(self, task_name: str, retry_count: int, queue: str | None = None) -> None:
        del retry_count
        task_label = self._normalize_label(task_name)
        queue_label = self._normalize_label(queue)
        self._task_total.labels(task_name=task_label, queue=queue_label, status="retry").inc()
        self._task_retry_total.labels(task_name=task_label, queue=queue_label).inc()

    def record_queue_size(self, queue: str, size: int) -> None:
        safe_size = max(0, int(size))
        self._queue_size.labels(queue=self._normalize_label(queue)).set(float(safe_size))

    def _normalize_label(self, value: Any) -> str:
        label = str(value or "").strip().lower()
        if not label:
            return _UNKNOWN_LABEL
        label = _LABEL_ALLOWED_RE.sub("_", label)
        if len(label) > _LABEL_MAX_LEN:
            return label[:_LABEL_MAX_LEN]
        return label

    def _get_or_create_counter(
        self,
        *,
        registry: Any,
        name: str,
        documentation: str,
        labelnames: tuple[str, ...],
    ) -> Any:
        try:
            return Counter(name=name, documentation=documentation, labelnames=labelnames, registry=registry)
        except ValueError:
            return getattr(registry, "_names_to_collectors", {}).get(name)

    def _get_or_create_histogram(
        self,
        *,
        registry: Any,
        name: str,
        documentation: str,
        labelnames: tuple[str, ...],
        buckets: tuple[float, ...],
    ) -> Any:
        try:
            return Histogram(
                name=name,
                documentation=documentation,
                labelnames=labelnames,
                buckets=buckets,
                registry=registry,
            )
        except ValueError:
            return getattr(registry, "_names_to_collectors", {}).get(name)

    def _get_or_create_gauge(
        self,
        *,
        registry: Any,
        name: str,
        documentation: str,
        labelnames: tuple[str, ...],
    ) -> Any:
        try:
            return Gauge(name=name, documentation=documentation, labelnames=labelnames, registry=registry)
        except ValueError:
            return getattr(registry, "_names_to_collectors", {}).get(name)


class TaskMetrics:
    """Facade for recording task-level metrics with graceful fallback behavior."""

    def __init__(self) -> None:
        try:
            self._backend: Any = _PrometheusTaskMetricsBackend()
        except Exception as exc:
            logger.debug("task_metrics_backend_unavailable", extra={"error": str(exc)})
            self._backend = _NoopTaskMetricsBackend()

    def record_task_started(self, task_name: str, queue: str | None = None) -> None:
        self._safe_call("record_task_started", task_name, queue)

    def record_task_success(self, task_name: str, duration_seconds: float, queue: str | None = None) -> None:
        self._safe_call("record_task_success", task_name, duration_seconds, queue)

    def record_task_failure(self, task_name: str, queue: str | None = None) -> None:
        self._safe_call("record_task_failure", task_name, queue)

    def record_task_retry(self, task_name: str, retry_count: int, queue: str | None = None) -> None:
        self._safe_call("record_task_retry", task_name, retry_count, queue)

    def record_queue_size(self, queue: str, size: int) -> None:
        self._safe_call("record_queue_size", queue, size)

    def _safe_call(self, method_name: str, *args: Any) -> None:
        try:
            method = getattr(self._backend, method_name)
            method(*args)
        except Exception:  # pragma: no cover - metrics should never break business flow
            logger.debug("task_metrics_recording_failed", extra={"method": method_name}, exc_info=True)
