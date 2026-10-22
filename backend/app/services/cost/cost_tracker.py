"""Cost tracking engine for provider usage, estimated spend, and cache savings."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.llm.contracts import CostSummarySnapshot, LLMRequest, LLMResponse, ProviderUsageRecord
from app.services.llm.model_costs import get_model_cost

UsageSource = Literal["live_provider_call", "cache_hit", "estimated_only"]


class CostUsageRecord(BaseModel):
    """Typed cost usage record for one request/session correlation event."""

    request_id: str | None = Field(default=None, min_length=1, max_length=128)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    provider: str = Field(..., min_length=1, max_length=64)
    model: str = Field(..., min_length=1, max_length=128)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    request_count: int = Field(default=1, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)
    cache_saved_cost_usd: float = Field(default=0.0, ge=0.0)
    source: UsageSource = "live_provider_call"
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CostTracker:
    """In-memory cost usage tracker decoupled from persistence or API concerns."""

    def __init__(self) -> None:
        self._records: list[CostUsageRecord] = []

    async def estimate_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> ProviderUsageRecord:
        """Estimate usage/cost for token counts using centralized pricing config."""
        prompt_tokens = max(input_tokens, 0)
        completion_tokens = max(output_tokens, 0)
        total_tokens = prompt_tokens + completion_tokens
        model_cost = get_model_cost(provider=provider, model=model)
        estimated_cost_usd = model_cost.estimate_cost_usd(prompt_tokens, completion_tokens) if model_cost else None
        return ProviderUsageRecord(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )

    async def record_usage(
        self,
        usage: ProviderUsageRecord,
        request_id: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        request_count: int = 1,
        cache_saved_cost_usd: float = 0.0,
        source: UsageSource = "live_provider_call",
    ) -> CostUsageRecord:
        """Record provider usage with optional request/session/user correlation."""
        estimated_cost = usage.estimated_cost_usd
        if estimated_cost is None:
            model_cost = get_model_cost(provider=usage.provider, model=usage.model)
            if model_cost:
                estimated_cost = model_cost.estimate_cost_usd(usage.prompt_tokens, usage.completion_tokens)
            else:
                estimated_cost = 0.0

        record = CostUsageRecord(
            request_id=request_id,
            session_id=session_id,
            user_id=user_id,
            provider=usage.provider,
            model=usage.model,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            request_count=max(request_count, 0),
            estimated_cost_usd=max(float(estimated_cost), 0.0),
            cache_saved_cost_usd=max(float(cache_saved_cost_usd), 0.0),
            source=source,
        )
        self._records.append(record)
        return record

    async def record_response(
        self,
        request: LLMRequest,
        response: LLMResponse,
        cache_saved_cost_usd: float = 0.0,
    ) -> CostUsageRecord:
        """Record a normalized LLM response and compute missing estimated costs."""
        usage = response.usage
        if usage is None:
            usage = await self.estimate_usage(
                provider=response.provider,
                model=response.model,
                input_tokens=0,
                output_tokens=0,
            )

        return await self.record_usage(
            usage=usage,
            request_id=request.request_id,
            session_id=request.session_id,
            user_id=request.user_id,
            cache_saved_cost_usd=cache_saved_cost_usd,
            source="live_provider_call",
        )

    async def record_cache_saving(
        self,
        request_id: str | None,
        provider: str,
        model: str,
        estimated_saved_cost_usd: float,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> CostUsageRecord:
        """Record a cache hit as cost saved without additional provider token spend."""
        usage = ProviderUsageRecord(
            provider=provider,
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost_usd=0.0,
        )
        return await self.record_usage(
            usage=usage,
            request_id=request_id,
            session_id=session_id,
            user_id=user_id,
            request_count=1,
            cache_saved_cost_usd=max(float(estimated_saved_cost_usd), 0.0),
            source="cache_hit",
        )

    async def get_summary(
        self,
        window_start: datetime,
        window_end: datetime,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> CostSummarySnapshot:
        """Aggregate cost and token metrics for the requested time window."""
        records = self._filter_records(window_start=window_start, window_end=window_end, user_id=user_id, session_id=session_id)

        total_requests = sum(item.request_count for item in records)
        total_prompt_tokens = sum(item.input_tokens for item in records)
        total_completion_tokens = sum(item.output_tokens for item in records)
        total_tokens = sum(item.total_tokens for item in records)
        total_estimated_cost_usd = round(sum(item.estimated_cost_usd for item in records), 8)

        by_provider: dict[str, float] = {}
        for item in records:
            by_provider[item.provider] = round(by_provider.get(item.provider, 0.0) + item.estimated_cost_usd, 8)

        return CostSummarySnapshot(
            window_start=window_start,
            window_end=window_end,
            total_requests=total_requests,
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
            total_tokens=total_tokens,
            total_estimated_cost_usd=total_estimated_cost_usd,
            by_provider=by_provider,
        )

    async def get_cache_savings(
        self,
        window_start: datetime,
        window_end: datetime,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> float:
        """Aggregate cache-saved cost estimates for the requested window."""
        records = self._filter_records(window_start=window_start, window_end=window_end, user_id=user_id, session_id=session_id)
        return round(sum(item.cache_saved_cost_usd for item in records), 8)

    async def list_records(
        self,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> list[CostUsageRecord]:
        """Return recorded usage entries filtered by user/session if provided."""
        return [
            item
            for item in self._records
            if (user_id is None or item.user_id == user_id) and (session_id is None or item.session_id == session_id)
        ]

    def _filter_records(
        self,
        window_start: datetime,
        window_end: datetime,
        user_id: str | None,
        session_id: str | None,
    ) -> list[CostUsageRecord]:
        return [
            item
            for item in self._records
            if window_start <= item.recorded_at <= window_end
            and (user_id is None or item.user_id == user_id)
            and (session_id is None or item.session_id == session_id)
        ]
