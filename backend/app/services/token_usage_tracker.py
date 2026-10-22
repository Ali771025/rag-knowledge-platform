from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from time import perf_counter
from typing import Any
from uuid import UUID

from app.models.llm.contracts import LLMRequest, LLMResponse
from app.models.token_monitoring import TokenProvider
from app.services.token_monitoring import TokenPricingEngine
from app.services.token_usage_async import TokenUsageCaptureEvent, token_usage_async_logger

logger = logging.getLogger(__name__)


class TokenUsageTracker:
    def __init__(self, pricing_engine: TokenPricingEngine | None = None) -> None:
        self.pricing_engine = pricing_engine or TokenPricingEngine()

    async def track_llm_response(
        self,
        *,
        request: LLMRequest,
        response: LLMResponse,
        endpoint: str,
        cache_hit: bool = False,
        api_key_id: UUID | None = None,
        api_key_alias: str | None = None,
        started_at: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            provider = self._to_token_provider(response.provider)
            usage = response.usage
            prompt_tokens = max(int(usage.prompt_tokens if usage else 0), 0)
            completion_tokens = max(int(usage.completion_tokens if usage else 0), 0)
            total_tokens = max(int(usage.total_tokens if usage else prompt_tokens + completion_tokens), 0)

            if total_tokens <= 0:
                total_tokens = prompt_tokens + completion_tokens

            cost = self.pricing_engine.calculate_cost(
                provider=provider,
                model_name=response.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
            latency_ms = self._resolve_latency_ms(response=response, started_at=started_at)

            token_usage_async_logger.enqueue(
                TokenUsageCaptureEvent(
                    provider=provider,
                    model_name=response.model,
                    api_key_id=api_key_id,
                    api_key_alias=api_key_alias,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=max(total_tokens, prompt_tokens + completion_tokens),
                    cost_usd=cost.cost_usd,
                    latency_ms=latency_ms,
                    cache_hit=cache_hit,
                    endpoint=endpoint,
                    session_id=request.session_id,
                    request_id=request.request_id,
                    metadata=metadata or {},
                    created_at=datetime.now(timezone.utc),
                )
            )
        except Exception:
            logger.exception(
                "token_usage.capture_failed",
                extra={
                    "provider": str(getattr(response, "provider", "unknown")),
                    "model": str(getattr(response, "model", "unknown")),
                    "request_id": str(getattr(request, "request_id", "")),
                    "endpoint": endpoint,
                },
            )
        else:
            logger.debug(
                "token_usage.capture_enqueued",
                extra={
                    "provider": provider.value,
                    "model": response.model,
                    "request_id": request.request_id,
                    "endpoint": endpoint,
                    "cache_hit": cache_hit,
                },
            )

    async def track_cache_hit(
        self,
        *,
        session_id: str | None,
        endpoint: str,
        provider: str = "openai",
        model_name: str = "cache-hit",
        api_key_id: UUID | None = None,
        api_key_alias: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            provider_enum = self._to_token_provider(provider)
            token_usage_async_logger.enqueue(
                TokenUsageCaptureEvent(
                    provider=provider_enum,
                    model_name=model_name,
                    api_key_id=api_key_id,
                    api_key_alias=api_key_alias,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    cost_usd=Decimal("0"),
                    latency_ms=0,
                    cache_hit=True,
                    endpoint=endpoint,
                    session_id=session_id,
                    request_id=None,
                    metadata=metadata or {},
                    created_at=datetime.now(timezone.utc),
                )
            )
        except Exception:
            logger.exception(
                "token_usage.cache_capture_failed",
                extra={
                    "provider": provider,
                    "model": model_name,
                    "session_id": session_id,
                    "endpoint": endpoint,
                },
            )
        else:
            logger.debug(
                "token_usage.cache_capture_enqueued",
                extra={
                    "provider": provider_enum.value,
                    "model": model_name,
                    "session_id": session_id,
                    "endpoint": endpoint,
                },
            )

    @staticmethod
    def _resolve_latency_ms(*, response: LLMResponse, started_at: float | None) -> int:
        if isinstance(response.latency_ms, int) and response.latency_ms >= 0:
            return response.latency_ms
        if started_at is None:
            return 0
        return max(int((perf_counter() - started_at) * 1000), 0)

    @staticmethod
    def _to_token_provider(provider: str) -> TokenProvider:
        normalized = provider.strip().lower()
        if normalized == "claude":
            normalized = "anthropic"
        if normalized not in {"openai", "anthropic", "deepseek"}:
            return TokenProvider.OPENAI
        return TokenProvider(normalized)


token_usage_tracker = TokenUsageTracker()
