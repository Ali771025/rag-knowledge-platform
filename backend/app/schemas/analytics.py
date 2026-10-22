"""Internal admin analytics API schemas."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class AnalyticsSummaryResponse(BaseModel):
    requests_today: int
    active_sessions: int
    avg_latency_ms: float
    p95_latency_ms: float
    total_tokens_today: int
    total_cost_today: Decimal
    state_distribution: dict[str, int]
