"""Aggregation service for observability operational summaries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.observability.analytics_models import AnalyticsSummarySnapshot, now_utc
from app.repositories.conversation_log_repository import ConversationLogRepository
from app.repositories.cost_log_repository import CostLogRepository
from app.repositories.session_log_repository import SessionLogRepository


class AnalyticsSummaryService:
    """Builds dashboard-friendly observability summary snapshots."""

    def __init__(
        self,
        *,
        conversation_logs: ConversationLogRepository,
        cost_logs: CostLogRepository,
        session_logs: SessionLogRepository,
        currency: str = "USD",
    ) -> None:
        self.conversation_logs = conversation_logs
        self.cost_logs = cost_logs
        self.session_logs = session_logs
        self.currency = currency.strip().upper()

    def get_today_summary(self, *, now: datetime | None = None) -> AnalyticsSummarySnapshot:
        anchor = (now or now_utc()).astimezone(UTC)
        day_start = datetime(anchor.year, anchor.month, anchor.day, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)

        requests_today = self.conversation_logs.count_requests_today(now=anchor)
        active_sessions = self.session_logs.count_active_sessions(now=anchor)

        latency_inputs = self.conversation_logs.average_latency_summary_inputs(
            start_at=day_start,
            end_at=day_end,
        )
        latency_values = self.conversation_logs.list_latency_values(
            start_at=day_start,
            end_at=day_end,
        )

        avg_latency_ms = float(latency_inputs.average_latency_ms if latency_inputs.sample_count > 0 else 0.0)
        p95_latency_ms = self._compute_p95_latency(latency_values)

        total_tokens_today = self.cost_logs.aggregate_total_tokens(
            start_at=day_start,
            end_at=day_end,
            currency=self.currency,
        )
        total_cost_today = self.cost_logs.aggregate_total_cost(
            start_at=day_start,
            end_at=day_end,
            currency=self.currency,
        )

        state_distribution = self.conversation_logs.aggregate_state_distribution(
            start_at=day_start,
            end_at=day_end,
        )

        return AnalyticsSummarySnapshot(
            timestamp=anchor,
            period="day",
            period_date=day_start.date(),
            requests_today=requests_today,
            active_sessions=active_sessions,
            avg_latency_ms=avg_latency_ms,
            p95_latency_ms=p95_latency_ms,
            total_tokens_today=total_tokens_today,
            total_cost_today=Decimal(str(total_cost_today)),
            state_distribution=state_distribution,
            currency=self.currency,
        )

    def _compute_p95_latency(self, values: list[float]) -> float:
        if not values:
            return 0.0

        sorted_values = sorted(values)
        # Nearest-rank percentile with 1-based indexing.
        rank = int((0.95 * len(sorted_values)) + 0.999999)
        index = max(0, min(len(sorted_values) - 1, rank - 1))
        return float(sorted_values[index])
