"""Backend-agnostic LLM metrics and structured logging hooks."""

from __future__ import annotations

import logging
from typing import Any, Callable

from app.models.llm.contracts import LLMResponse, RoutingDecision

MetricEmitter = Callable[[str, float, dict[str, str]], None]


class LLMMetricsRecorder:
    """Fault-isolated LLM metrics recorder with no-op-safe behavior."""

    def __init__(self, emit_metric: MetricEmitter | None = None, logger_name: str | None = None) -> None:
        self.emit_metric = emit_metric
        self.logger = logging.getLogger(logger_name or __name__)
        self._counters: dict[str, float] = {
            "router_decision_count": 0.0,
            "provider_latency_ms_total": 0.0,
            "provider_latency_count": 0.0,
            "fallback_count": 0.0,
            "llm_prompt_tokens": 0.0,
            "llm_completion_tokens": 0.0,
            "llm_total_tokens": 0.0,
            "llm_estimated_cost_usd": 0.0,
            "llm_response_count": 0.0,
        }

    def record_router_decision(self, decision: RoutingDecision) -> None:
        """Record router decisions and selected provider/model."""
        self._counters["router_decision_count"] += 1
        self._emit("router_decision_count", 1.0, provider=decision.provider, model=decision.model)
        if decision.estimated_cost_usd is not None:
            self._emit("router_decision_estimated_cost_usd", float(decision.estimated_cost_usd), provider=decision.provider)
        self._log_debug("router_decision", provider=decision.provider, model=decision.model, reason=decision.reason)

    def record_provider_latency(self, provider: str, model: str, latency_ms: int) -> None:
        """Record observed provider latency in milliseconds."""
        self._counters["provider_latency_ms_total"] += max(float(latency_ms), 0.0)
        self._counters["provider_latency_count"] += 1
        self._emit("provider_latency_ms", float(max(latency_ms, 0)), provider=provider, model=model)

    def record_fallback(self, from_provider: str, to_provider: str) -> None:
        """Record a provider fallback/failover transition."""
        self._counters["fallback_count"] += 1
        self._emit("fallback_count", 1.0, from_provider=from_provider, to_provider=to_provider)
        self._log_debug("provider_fallback", from_provider=from_provider, to_provider=to_provider)

    def record_token_usage(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
    ) -> None:
        """Record token usage counters."""
        self._counters["llm_prompt_tokens"] += max(float(prompt_tokens), 0.0)
        self._counters["llm_completion_tokens"] += max(float(completion_tokens), 0.0)
        self._counters["llm_total_tokens"] += max(float(total_tokens), 0.0)
        self._emit("llm_prompt_tokens", float(max(prompt_tokens, 0)), provider=provider, model=model)
        self._emit("llm_completion_tokens", float(max(completion_tokens, 0)), provider=provider, model=model)
        self._emit("llm_total_tokens", float(max(total_tokens, 0)), provider=provider, model=model)

    def record_estimated_cost(self, provider: str, model: str, estimated_cost_usd: float) -> None:
        """Record estimated LLM call cost."""
        self._counters["llm_estimated_cost_usd"] += max(float(estimated_cost_usd), 0.0)
        self._emit("llm_estimated_cost_usd", float(max(estimated_cost_usd, 0.0)), provider=provider, model=model)

    def record_response(self, response: LLMResponse) -> None:
        """Record normalized response metadata for usage/cost/latency metrics."""
        self._counters["llm_response_count"] += 1
        self._emit("llm_response_count", 1.0, provider=response.provider, model=response.model)
        if response.latency_ms is not None:
            self.record_provider_latency(response.provider, response.model, response.latency_ms)
        if response.usage is not None:
            self.record_token_usage(
                provider=response.provider,
                model=response.model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
            if response.usage.estimated_cost_usd is not None:
                self.record_estimated_cost(response.provider, response.model, response.usage.estimated_cost_usd)
        self._log_debug("llm_response", provider=response.provider, model=response.model, request_id=response.request_id)

    def _emit(self, name: str, value: float, **labels: str) -> None:
        if self.emit_metric is None:
            return
        try:
            self.emit_metric(name, value, labels)
        except Exception as exc:  # pragma: no cover - metrics backend isolation
            self.logger.debug("llm metrics emit failed: metric=%s error=%s", name, exc)

    def _log_debug(self, event: str, **fields: Any) -> None:
        self.logger.debug("llm_event=%s fields=%s", event, fields)

    def snapshot(self) -> dict[str, float]:
        """Return in-process LLM observability counters."""
        latency_count = self._counters["provider_latency_count"]
        avg_latency = 0.0 if latency_count <= 0 else self._counters["provider_latency_ms_total"] / latency_count
        return {
            "router_decision_count": self._counters["router_decision_count"],
            "provider_latency_ms_avg": round(avg_latency, 4),
            "fallback_count": self._counters["fallback_count"],
            "llm_prompt_tokens": self._counters["llm_prompt_tokens"],
            "llm_completion_tokens": self._counters["llm_completion_tokens"],
            "llm_total_tokens": self._counters["llm_total_tokens"],
            "llm_estimated_cost_usd": round(self._counters["llm_estimated_cost_usd"], 8),
            "llm_response_count": self._counters["llm_response_count"],
        }
