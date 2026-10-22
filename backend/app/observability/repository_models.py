"""Typed read models returned by observability repositories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class CostByPeriodAggregate:
    """Aggregated monetary cost for a user and time period."""

    period_start: date
    total_cost: Decimal
    currency: str


@dataclass(frozen=True, slots=True)
class CostByStateAggregate:
    """Aggregated monetary cost grouped by state."""

    state: str
    total_cost: Decimal
    currency: str


@dataclass(frozen=True, slots=True)
class LatencySummaryInputs:
    """Pre-aggregated inputs for computing latency summary statistics."""

    sample_count: int
    total_latency_ms: float
    average_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
