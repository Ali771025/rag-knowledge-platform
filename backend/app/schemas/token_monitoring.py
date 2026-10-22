from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.token_monitoring import RecommendationCategory, RecommendationSeverity, TokenProvider


class APIKeyCreateRequest(BaseModel):
    provider: TokenProvider
    display_name: str = Field(min_length=1, max_length=128)
    raw_key: str = Field(min_length=8, max_length=1024)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, protected_namespaces=())


class APIKeyResponse(BaseModel):
    id: UUID
    provider: TokenProvider
    display_name: str
    key_alias: str | None
    key_fingerprint: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class TokenUsageLogResponse(BaseModel):
    id: UUID
    api_key_id: UUID
    provider: TokenProvider
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: Decimal
    request_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class DailyAggregateResponse(BaseModel):
    id: UUID
    api_key_id: UUID
    date: date
    total_requests: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    total_cost_usd: Decimal

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class OptimizationRecommendationResponse(BaseModel):
    id: UUID
    api_key_id: UUID | None
    category: RecommendationCategory
    severity: RecommendationSeverity
    title: str
    summary: str
    generated_at: datetime
    is_dismissed: bool

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class BudgetAlertResponse(BaseModel):
    id: UUID
    api_key_id: UUID
    threshold_usd: Decimal
    current_spend_usd: Decimal
    period: str
    triggered_at: datetime
    acknowledged_at: datetime | None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class CostCalculationRequest(BaseModel):
    provider: TokenProvider
    model_name: str = Field(min_length=1, max_length=128)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, protected_namespaces=())


class CostCalculationResponse(BaseModel):
    provider: TokenProvider
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: Decimal
    pricing_found: bool

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, protected_namespaces=())
