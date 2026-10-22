"""Typed models for observability analytics summaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Mapping


@dataclass(frozen=True, slots=True)
class AnalyticsSummarySnapshot:
    """Aggregate summary used by internal operational dashboards."""

    timestamp: datetime
    period: str
    period_date: date
    requests_today: int
    active_sessions: int
    avg_latency_ms: float
    p95_latency_ms: float
    total_tokens_today: int
    total_cost_today: Decimal
    state_distribution: Mapping[str, int]
    currency: str = "USD"


def now_utc() -> datetime:
    return datetime.now(UTC)
