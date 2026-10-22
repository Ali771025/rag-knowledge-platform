"""Provider-agnostic unified LLM client interface and normalization layer."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from app.models.llm.contracts import LLMRequest, LLMResponse, ProviderUsageRecord, RoutingDecision


class UnifiedClientError(RuntimeError):
    """Base error for unified LLM client operations."""


class LLMTimeoutError(UnifiedClientError):
    """Raised when provider generation exceeds the configured timeout."""


class RetryableLLMError(UnifiedClientError):
    """Raised by adapters to indicate a transient and retryable failure."""


class ProviderExecutionError(UnifiedClientError):
    """Raised when provider execution fails and cannot be recovered."""


class ProviderLLMAdapter(Protocol):
    """Provider adapter boundary for request execution."""

    provider_name: str

    async def generate(self, request: LLMRequest, routing: RoutingDecision) -> Any:
        """Execute provider-specific generation and return raw payload."""


@dataclass(slots=True)
class UnifiedClientConfig:
    """Execution boundaries for timeouts and retries."""

    timeout_seconds: float = 30.0
    max_retries: int = 1
    retry_backoff_seconds: float = 0.5


class _BaseProviderAdapter:
    """Minimal base adapter placeholder for provider-specific implementations."""

    provider_name: str = "base"

    async def generate(self, request: LLMRequest, routing: RoutingDecision) -> Any:
        _ = (request, routing)
        raise ProviderExecutionError(
            f"Provider adapter '{self.provider_name}' is not wired yet. "
            "Register a concrete adapter via UnifiedLLMClient.register_adapter(...)."
        )


class AnthropicAdapter(_BaseProviderAdapter):
    """Placeholder adapter boundary for Anthropic implementations."""

    provider_name = "claude"


class OpenAIAdapter(_BaseProviderAdapter):
    """Placeholder adapter boundary for OpenAI implementations."""

    provider_name = "openai"


class GeminiAdapter(_BaseProviderAdapter):
    """Placeholder adapter boundary for Gemini implementations."""

    provider_name = "gemini"


class DeepSeekAdapter(_BaseProviderAdapter):
    """Placeholder adapter boundary for DeepSeek implementations."""

    provider_name = "deepseek"


class UnifiedLLMClient:
    """Unified interface that normalizes responses and isolates provider details."""

    def __init__(
        self,
        adapters: dict[str, ProviderLLMAdapter] | None = None,
        config: UnifiedClientConfig | None = None,
    ) -> None:
        self.config = config or UnifiedClientConfig()
        self._adapters: dict[str, ProviderLLMAdapter] = adapters or self._default_adapters()

    async def generate_response(self, request: LLMRequest, routing: RoutingDecision) -> LLMResponse:
        """Generate a normalized LLM response with timeout and bounded retries."""
        adapter = self._resolve_adapter(routing.provider)
        last_error: Exception | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                raw_payload = await asyncio.wait_for(
                    adapter.generate(request=request, routing=routing),
                    timeout=self.config.timeout_seconds,
                )
                return self._normalize_response(
                    request=request,
                    routing=routing,
                    raw_payload=raw_payload,
                )
            except asyncio.TimeoutError as exc:
                last_error = LLMTimeoutError(
                    f"Timed out after {self.config.timeout_seconds:.2f}s for provider={routing.provider} model={routing.model}."
                )
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_backoff_seconds * (2**attempt))
                    continue
                raise last_error from exc
            except RetryableLLMError as exc:
                last_error = exc
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_backoff_seconds * (2**attempt))
                    continue
                raise
            except ProviderExecutionError:
                raise
            except Exception as exc:
                raise ProviderExecutionError(
                    f"Provider execution failed for provider={routing.provider} model={routing.model}."
                ) from exc

        raise ProviderExecutionError("LLM generation failed without a concrete provider error.") from last_error

    async def generate(self, request: LLMRequest, routing: RoutingDecision) -> LLMResponse:
        """Backward-compatible alias for unified response generation."""
        return await self.generate_response(request=request, routing=routing)

    def register_adapter(self, provider: str, adapter: ProviderLLMAdapter) -> None:
        """Register or replace an adapter implementation for a provider."""
        self._adapters[provider.lower().strip()] = adapter

    def _resolve_adapter(self, provider: str) -> ProviderLLMAdapter:
        key = provider.lower().strip()
        adapter = self._adapters.get(key)
        if adapter is None:
            raise ProviderExecutionError(
                f"No adapter registered for provider='{provider}'."
            )
        return adapter

    def _normalize_response(
        self,
        request: LLMRequest,
        routing: RoutingDecision,
        raw_payload: Any,
    ) -> LLMResponse:
        if isinstance(raw_payload, LLMResponse):
            return raw_payload.model_copy(
                update={
                    "request_id": request.request_id,
                    "provider": routing.provider,
                    "model": routing.model,
                }
            )

        if not isinstance(raw_payload, dict):
            raise ProviderExecutionError(
                "Provider adapter must return a dict or LLMResponse for normalization."
            )

        output_text = self._extract_output_text(raw_payload)
        usage = self._extract_usage(
            provider=routing.provider,
            model=routing.model,
            usage_payload=raw_payload.get("usage"),
        )

        finish_reason = raw_payload.get("finish_reason") or raw_payload.get("stop_reason")
        if finish_reason is not None:
            finish_reason = str(finish_reason)

        latency_ms = raw_payload.get("latency_ms")
        if not isinstance(latency_ms, int):
            latency_ms = None

        return LLMResponse(
            request_id=request.request_id,
            provider=routing.provider,
            model=routing.model,
            output_text=output_text,
            finish_reason=finish_reason,
            usage=usage,
            latency_ms=latency_ms,
            raw_payload=raw_payload,
            responded_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _extract_output_text(payload: dict[str, Any]) -> str:
        for key in ("output_text", "text", "content"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
        raise ProviderExecutionError("Unable to normalize provider response: missing text content.")

    @staticmethod
    def _extract_usage(provider: str, model: str, usage_payload: Any) -> ProviderUsageRecord | None:
        if not isinstance(usage_payload, dict):
            return None

        prompt_tokens = usage_payload.get("prompt_tokens") or usage_payload.get("input_tokens") or 0
        completion_tokens = usage_payload.get("completion_tokens") or usage_payload.get("output_tokens") or 0
        total_tokens = usage_payload.get("total_tokens")

        if not isinstance(prompt_tokens, int):
            prompt_tokens = 0
        if not isinstance(completion_tokens, int):
            completion_tokens = 0
        if not isinstance(total_tokens, int):
            total_tokens = prompt_tokens + completion_tokens

        estimated_cost_usd = usage_payload.get("estimated_cost_usd")
        if not isinstance(estimated_cost_usd, (int, float)):
            estimated_cost_usd = None

        return ProviderUsageRecord(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=float(estimated_cost_usd) if estimated_cost_usd is not None else None,
        )

    @staticmethod
    def _default_adapters() -> dict[str, ProviderLLMAdapter]:
        return {
            "claude": AnthropicAdapter(),
            "openai": OpenAIAdapter(),
            "gemini": GeminiAdapter(),
            "deepseek": DeepSeekAdapter(),
        }
