"""Typed models for dependency health checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.observability.enums import HealthState
from app.observability.models import DependencyHealthResult


@dataclass(frozen=True, slots=True)
class HealthCheckReport:
    """Snapshot of dependency probe results and overall status."""

    checked_at: datetime
    overall_status: str
    overall_state: HealthState
    results: tuple[DependencyHealthResult, ...]


def derive_overall_state(results: tuple[DependencyHealthResult, ...]) -> HealthState:
    if not results:
        return HealthState.DEGRADED
    if all(result.state is HealthState.HEALTHY for result in results):
        return HealthState.HEALTHY
    return HealthState.DEGRADED


def derive_overall_status(overall_state: HealthState) -> str:
    return "healthy" if overall_state is HealthState.HEALTHY else "degraded"


def now_utc() -> datetime:
    return datetime.now(UTC)
