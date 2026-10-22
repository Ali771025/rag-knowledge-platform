"""Typed models for cost tracking service outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.observability.value_objects import CostRecord


@dataclass(frozen=True, slots=True)
class CostLogEntryResult:
    """Result payload returned after persisting a cost event."""

    log_id: UUID
    user_id: UUID | None
    request_id: str | None
    state: str
    endpoint: str | None
    cost: CostRecord
    usage_date: date


@dataclass(frozen=True, slots=True)
class CostTotalResult:
    """Generic aggregate total for a selected period."""

    period: str
    currency: str
    total_cost: Decimal


@dataclass(frozen=True, slots=True)
class ProjectedMonthlyCostResult:
    """Simple run-rate projection based on month-to-date spend."""

    month_start: date
    current_date: date
    elapsed_days: int
    days_in_month: int
    accrued_cost: Decimal
    projected_total_cost: Decimal
    currency: str
