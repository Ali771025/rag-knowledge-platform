"""Repository contracts for observability persistence and aggregates."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.models.conversation_log import ConversationLog
from app.models.cost_log import CostLog
from app.models.session_log import SessionLog
from app.observability.repository_models import (
    CostByPeriodAggregate,
    CostByStateAggregate,
    LatencySummaryInputs,
)


class ConversationLogRepositoryContract(Protocol):
    """Persistence and query contract for conversation observability logs."""

    def create(self, **fields: object) -> ConversationLog:
        """Persist and return a conversation log entry."""

    def count_requests_today(self, *, now: datetime | None = None) -> int:
        """Count request records created during the current UTC day."""

    def average_latency_summary_inputs(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        state: str | None = None,
        endpoint: str | None = None,
    ) -> LatencySummaryInputs:
        """Return pre-aggregated latency values for reporting."""


class CostLogRepositoryContract(Protocol):
    """Persistence and query contract for cost observability logs."""

    def create(self, **fields: object) -> CostLog:
        """Persist and return a cost log entry."""

    def aggregate_cost_by_user_day(
        self,
        *,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        currency: str | None = None,
    ) -> list[CostByPeriodAggregate]:
        """Aggregate user cost totals by day."""

    def aggregate_cost_by_user_month(
        self,
        *,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        currency: str | None = None,
    ) -> list[CostByPeriodAggregate]:
        """Aggregate user cost totals by month."""

    def aggregate_cost_by_state(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        currency: str | None = None,
    ) -> list[CostByStateAggregate]:
        """Aggregate cost totals grouped by processing state."""

    def aggregate_total_cost(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        currency: str | None = None,
    ) -> Decimal:
        """Aggregate total cost for a selected time range."""

    def aggregate_total_cost_by_user(
        self,
        *,
        user_id: UUID,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        currency: str | None = None,
    ) -> Decimal:
        """Aggregate total cost for one user and time range."""

    def aggregate_total_cost_for_state(
        self,
        *,
        state: str,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        currency: str | None = None,
    ) -> Decimal:
        """Aggregate total cost for one state and time range."""


class SessionLogRepositoryContract(Protocol):
    """Persistence and query contract for session observability logs."""

    def create(self, **fields: object) -> SessionLog:
        """Persist and return a session log entry."""

    def count_active_sessions(self, *, now: datetime | None = None) -> int:
        """Count currently active sessions based on lifecycle state and timestamps."""
