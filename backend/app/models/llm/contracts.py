"""Shared typed contracts for routing and LLM services."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class LLMMessage(BaseModel):
    """A single role/content message payload for LLM providers."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProviderUsageRecord(BaseModel):
    """Provider token usage and cost attribution for one request."""

    provider: str = Field(..., min_length=1, max_length=64)
    model: str = Field(..., min_length=1, max_length=128)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LLMRequest(BaseModel):
    """Normalized request contract used across routing and provider clients."""

    request_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=128)
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    prompt: str = Field(..., min_length=1)
    system_prompt: str | None = None
    messages: list[LLMMessage] = Field(default_factory=list)
    candidate_models: list[str] = Field(default_factory=list)
    max_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ComplexityResult(BaseModel):
    """Complexity classification output for routing decisions."""

    label: Literal["simple", "medium", "complex", "high_risk"]
    score: float = Field(..., ge=0.0, le=1.0)
    estimated_input_tokens: int = Field(default=0, ge=0)
    rationale: str | None = Field(default=None, min_length=1, max_length=512)
    risk_tags: list[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RoutingDecision(BaseModel):
    """Provider/model decision returned by routing modules."""

    provider: str = Field(..., min_length=1, max_length=64)
    model: str = Field(..., min_length=1, max_length=128)
    reason: str = Field(..., min_length=1, max_length=512)
    fallback_provider: str | None = Field(default=None, min_length=1, max_length=64)
    fallback_model: str | None = Field(default=None, min_length=1, max_length=128)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    complexity: ComplexityResult | None = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LLMResponse(BaseModel):
    """Normalized response contract returned by unified LLM clients."""

    request_id: str = Field(..., min_length=1, max_length=128)
    provider: str = Field(..., min_length=1, max_length=64)
    model: str = Field(..., min_length=1, max_length=128)
    output_text: str = Field(..., min_length=1)
    finish_reason: str | None = Field(default=None, min_length=1, max_length=128)
    usage: ProviderUsageRecord | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    raw_payload: dict[str, Any] | None = None
    responded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CostSummarySnapshot(BaseModel):
    """Time-bounded cost aggregation contract for guardrails/admin views."""

    window_start: datetime
    window_end: datetime
    total_requests: int = Field(default=0, ge=0)
    total_prompt_tokens: int = Field(default=0, ge=0)
    total_completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    total_estimated_cost_usd: float = Field(default=0.0, ge=0.0)
    by_provider: dict[str, float] = Field(default_factory=dict)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
