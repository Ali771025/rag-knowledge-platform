"""Backend-agnostic cache metrics/logging hook implementation."""

from __future__ import annotations

import logging
from typing import Any, Callable

from app.models.cache.contracts import SemanticCacheLookupResult

MetricEmitter = Callable[[str, float, dict[str, str]], None]


class CacheMetricsRecorder:
    """Non-invasive cache metrics recorder with pluggable backend emitter."""

    def __init__(self, emit_metric: MetricEmitter | None = None, logger_name: str | None = None) -> None:
        self.emit_metric = emit_metric
        self.logger = logging.getLogger(logger_name or __name__)
        self._counters: dict[str, float] = {
            "semantic_cache_hit": 0.0,
            "semantic_cache_miss": 0.0,
            "semantic_cache_lookup_latency_ms_total": 0.0,
            "semantic_cache_lookup_count": 0.0,
            "semantic_cache_estimated_cost_saved_total": 0.0,
        }

    def semantic_cache_hit(self, namespace: str, latency_ms: int, **_: Any) -> None:
        """Hook for semantic cache hit count and log event."""
        self._counters["semantic_cache_hit"] += 1
        self._emit("semantic_cache_hit", 1.0, namespace=namespace)
        self._log_debug("semantic_cache_hit", namespace=namespace, latency_ms=latency_ms)

    def semantic_cache_miss(self, namespace: str, latency_ms: int, reason: str | None = None, **_: Any) -> None:
        """Hook for semantic cache miss count and reason tags."""
        self._counters["semantic_cache_miss"] += 1
        labels = {"namespace": namespace}
        if reason:
            labels["reason"] = reason
        self._emit("semantic_cache_miss", 1.0, **labels)
        self._log_debug("semantic_cache_miss", namespace=namespace, latency_ms=latency_ms, reason=reason)

    def semantic_cache_lookup_latency_ms(self, namespace: str, latency_ms: int, **_: Any) -> None:
        """Hook for semantic cache lookup latency observation."""
        self._counters["semantic_cache_lookup_latency_ms_total"] += max(float(latency_ms), 0.0)
        self._counters["semantic_cache_lookup_count"] += 1
        self._emit("semantic_cache_lookup_latency_ms", float(latency_ms), namespace=namespace)

    def semantic_cache_similarity_score(self, namespace: str, score: float, **_: Any) -> None:
        """Hook for semantic similarity score observation."""
        self._emit("semantic_cache_similarity_score", float(score), namespace=namespace)

    def semantic_cache_estimated_cost_saved(self, namespace: str, estimated_cost_saved: float, **_: Any) -> None:
        """Hook for estimated provider cost avoided due to cache hits."""
        self._counters["semantic_cache_estimated_cost_saved_total"] += max(float(estimated_cost_saved), 0.0)
        self._emit("semantic_cache_estimated_cost_saved", float(estimated_cost_saved), namespace=namespace)

    def record_semantic_lookup(self, result: SemanticCacheLookupResult) -> None:
        """Backward-compatible entry point for semantic lookup tracking."""
        namespace = result.response.namespace if result.response is not None else "semantic"
        self.semantic_cache_lookup_latency_ms(namespace=namespace, latency_ms=0)
        if result.similarity_score is not None:
            self.semantic_cache_similarity_score(namespace=namespace, score=result.similarity_score)

        if result.hit:
            self.semantic_cache_hit(namespace=namespace, latency_ms=0)
        else:
            self.semantic_cache_miss(namespace=namespace, latency_ms=0, reason=result.reason)

    def _emit(self, name: str, value: float, **labels: str) -> None:
        if self.emit_metric is None:
            return
        try:
            self.emit_metric(name, value, labels)
        except Exception as exc:  # pragma: no cover - fault isolation from metrics backend
            self.logger.debug("cache metrics emit failed: metric=%s error=%s", name, exc)

    def _log_debug(self, event: str, **fields: Any) -> None:
        self.logger.debug("cache_event=%s fields=%s", event, fields)

    def snapshot(self) -> dict[str, float]:
        """Return in-process cache observability counters."""
        lookups = self._counters["semantic_cache_lookup_count"]
        avg_latency = 0.0 if lookups <= 0 else self._counters["semantic_cache_lookup_latency_ms_total"] / lookups
        return {
            "semantic_cache_hit": self._counters["semantic_cache_hit"],
            "semantic_cache_miss": self._counters["semantic_cache_miss"],
            "semantic_cache_lookup_count": lookups,
            "semantic_cache_lookup_latency_ms_avg": round(avg_latency, 4),
            "semantic_cache_estimated_cost_saved_total": round(
                self._counters["semantic_cache_estimated_cost_saved_total"], 8
            ),
        }
