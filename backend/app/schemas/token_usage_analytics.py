from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.token_monitoring import TokenProvider

Granularity = Literal["hourly", "daily", "weekly", "monthly"]


class TokenUsageSummaryPoint(BaseModel):
    bucket_start: datetime
    provider: str
    model_name: str
    api_key_id: UUID | None
    total_cost_usd: Decimal = Field(ge=Decimal("0"))
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    request_count: int = Field(ge=0)
    avg_latency_ms: float = Field(ge=0)
    cache_hit_rate: float = Field(ge=0, le=1)

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class ProviderCostBreakdown(BaseModel):
    provider: str
    total_cost_usd: Decimal = Field(ge=Decimal("0"))

    model_config = ConfigDict(extra="forbid")


class TokenUsageSummaryResponse(BaseModel):
    granularity: Granularity
    points: list[TokenUsageSummaryPoint]
    provider_cost_breakdown: list[ProviderCostBreakdown]

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class ModelUsageMetrics(BaseModel):
    provider: str
    model_name: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    total_cost_usd: Decimal = Field(ge=Decimal("0"))
    request_count: int = Field(ge=0)
    avg_latency_ms: float = Field(ge=0)
    cache_hit_rate: float = Field(ge=0, le=1)

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class TokenUsageByModelResponse(BaseModel):
    items: list[ModelUsageMetrics]

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class RecentRequestUsageItem(BaseModel):
    id: UUID
    request_id: str | None
    provider: TokenProvider
    model_name: str
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cost_usd: Decimal = Field(ge=Decimal("0"))
    latency_ms: int = Field(ge=0)
    cache_hit: bool
    endpoint: str | None
    session_id: str | None
    created_at: datetime

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class PaginatedRecentRequests(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)
    total: int = Field(ge=0)
    items: list[RecentRequestUsageItem]

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class BudgetInfo(BaseModel):
    current_spend_usd: Decimal = Field(ge=Decimal("0"))
    period: str
    monthly_budget_usd: Decimal | None = Field(default=None, ge=Decimal("0"))
    alert_thresholds: list[int] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class APIKeyUsageDetailsResponse(BaseModel):
    api_key: dict
    time_series: list[TokenUsageSummaryPoint]
    recent_requests: PaginatedRecentRequests
    budget: BudgetInfo | None = None

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class CostForecastResponse(BaseModel):
    current_spend_usd: Decimal = Field(ge=Decimal("0"))
    projected_spend_usd: Decimal = Field(ge=Decimal("0"))
    confidence: Literal["low", "medium", "high"]
    confidence_note: str
    period_start: date
    period_end: date

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class TokenUsageRealtimeEvent(BaseModel):
    timestamp: datetime
    provider: str
    model_name: str
    api_key_id: str | None
    tokens_delta: int = Field(ge=0)
    cost_delta: Decimal = Field(ge=Decimal("0"))
    latency_ms: int = Field(ge=0)
    cache_hit: bool

    model_config = ConfigDict(extra="forbid", protected_namespaces=())
