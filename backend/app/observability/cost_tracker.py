"""Cost tracking service for token-based pricing and persistence."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from app.observability.cost_models import CostLogEntryResult, CostTotalResult, ProjectedMonthlyCostResult
from app.observability.exceptions import ObservabilityContractError
from app.observability.value_objects import CostRecord
from app.repositories.cost_log_repository import CostLogRepository

_DECIMAL_NANO_USD = Decimal("0.000000001")


@dataclass(frozen=True, slots=True)
class ProviderPricingConfig:
    """Token pricing configuration for a provider/model family.

    Values represent USD per 1 million tokens.
    """

    input_usd_per_million_tokens: Decimal = Decimal("3")
    output_usd_per_million_tokens: Decimal = Decimal("15")


class CostTracker:
    """Service for calculating and persisting token-based request costs."""

    def __init__(
        self,
        repository: CostLogRepository,
        *,
        pricing: ProviderPricingConfig | None = None,
        currency: str = "USD",
    ) -> None:
        self.repository = repository
        self.pricing = pricing or ProviderPricingConfig()
        self.currency = currency.strip().upper()
        if len(self.currency) != 3:
            raise ObservabilityContractError("`currency` must be a 3-letter code.")

    def calculate_request_cost(self, input_tokens: int, output_tokens: int) -> CostRecord:
        """Compute request cost from input/output token counts."""

        if input_tokens < 0 or output_tokens < 0:
            raise ObservabilityContractError("Token counts cannot be negative.")

        input_cost = self._cost_from_tokens(
            token_count=input_tokens,
            usd_per_million_tokens=self.pricing.input_usd_per_million_tokens,
        )
        output_cost = self._cost_from_tokens(
            token_count=output_tokens,
            usd_per_million_tokens=self.pricing.output_usd_per_million_tokens,
        )
        total_cost = (input_cost + output_cost).quantize(_DECIMAL_NANO_USD, rounding=ROUND_HALF_UP)

        return CostRecord(
            total_cost=total_cost,
            currency=self.currency,
            prompt_cost=input_cost,
            completion_cost=output_cost,
        )

    def log_cost(
        self,
        user_id: UUID | None,
        request_id: str,
        input_tokens: int,
        output_tokens: int,
        state: str,
        endpoint: str | None = None,
        *,
        trace_id: str | None = None,
    ) -> CostLogEntryResult:
        """Calculate and persist a cost log entry through the repository layer."""

        normalized_request_id = request_id.strip()
        if not normalized_request_id:
            raise ObservabilityContractError("`request_id` must be a non-empty string.")

        normalized_state = state.strip()
        if not normalized_state:
            raise ObservabilityContractError("`state` must be a non-empty string.")

        cost = self.calculate_request_cost(input_tokens=input_tokens, output_tokens=output_tokens)
        now = datetime.now(UTC)

        log = self.repository.create(
            user_id=user_id,
            session_id=None,
            request_id=normalized_request_id,
            trace_id=(trace_id or normalized_request_id),
            state=normalized_state,
            currency=cost.currency,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            prompt_cost=cost.prompt_cost,
            completion_cost=cost.completion_cost,
            cache_cost=cost.cache_cost,
            total_cost=cost.total_cost,
            metadata_json={
                "endpoint": endpoint,
            },
            created_at=now,
        )

        return CostLogEntryResult(
            log_id=log.id,
            user_id=log.user_id,
            request_id=log.request_id,
            state=log.state,
            endpoint=endpoint,
            cost=cost,
            usage_date=now.date(),
        )

    def get_user_cost(self, user_id: UUID, period: str = "day") -> CostTotalResult:
        """Return aggregate user cost for the selected period."""

        start_at, end_at, normalized_period = self._period_window(period)
        total = self.repository.aggregate_total_cost_by_user(
            user_id=user_id,
            start_at=start_at,
            end_at=end_at,
            currency=self.currency,
        )
        return CostTotalResult(period=normalized_period, currency=self.currency, total_cost=total)

    def get_total_cost(self, period: str = "day") -> CostTotalResult:
        """Return aggregate total cost for the selected period."""

        start_at, end_at, normalized_period = self._period_window(period)
        total = self.repository.aggregate_total_cost(
            start_at=start_at,
            end_at=end_at,
            currency=self.currency,
        )
        return CostTotalResult(period=normalized_period, currency=self.currency, total_cost=total)

    def get_cost_by_state(self, state: str, period: str = "day") -> CostTotalResult:
        """Return aggregate cost for one state over the selected period."""

        normalized_state = state.strip()
        if not normalized_state:
            raise ObservabilityContractError("`state` must be a non-empty string.")

        start_at, end_at, normalized_period = self._period_window(period)
        matched_total = self.repository.aggregate_total_cost_for_state(
            state=normalized_state,
            start_at=start_at,
            end_at=end_at,
            currency=self.currency,
        )

        return CostTotalResult(period=normalized_period, currency=self.currency, total_cost=matched_total)

    def get_projected_monthly_cost(self) -> ProjectedMonthlyCostResult:
        """Project monthly spend from month-to-date run-rate."""

        now = datetime.now(UTC)
        month_start = datetime(now.year, now.month, 1, tzinfo=UTC)
        next_month_start = self._next_month_start(month_start)

        accrued_cost = self.repository.aggregate_total_cost(
            start_at=month_start,
            end_at=next_month_start,
            currency=self.currency,
        )

        days_in_month = monthrange(now.year, now.month)[1]
        elapsed_days = max(1, now.day)

        projected = (accrued_cost / Decimal(elapsed_days)) * Decimal(days_in_month)
        projected = projected.quantize(_DECIMAL_NANO_USD, rounding=ROUND_HALF_UP)

        return ProjectedMonthlyCostResult(
            month_start=month_start.date(),
            current_date=now.date(),
            elapsed_days=elapsed_days,
            days_in_month=days_in_month,
            accrued_cost=accrued_cost,
            projected_total_cost=projected,
            currency=self.currency,
        )

    def _cost_from_tokens(self, *, token_count: int, usd_per_million_tokens: Decimal) -> Decimal:
        return (
            (Decimal(token_count) / Decimal("1000000")) * Decimal(usd_per_million_tokens)
        ).quantize(_DECIMAL_NANO_USD, rounding=ROUND_HALF_UP)

    def _period_window(self, period: str) -> tuple[datetime, datetime, str]:
        normalized_period = period.strip().lower()
        if not normalized_period:
            raise ObservabilityContractError("`period` must be a non-empty string.")

        now = datetime.now(UTC)

        if normalized_period == "day":
            start = datetime(now.year, now.month, now.day, tzinfo=UTC)
            end = start + timedelta(days=1)
            return start, end, normalized_period

        if normalized_period == "month":
            start = datetime(now.year, now.month, 1, tzinfo=UTC)
            end = self._next_month_start(start)
            return start, end, normalized_period

        raise ObservabilityContractError("Unsupported period. Use `day` or `month`.")

    def _next_month_start(self, month_start: datetime) -> datetime:
        if month_start.month == 12:
            return datetime(month_start.year + 1, 1, 1, tzinfo=UTC)
        return datetime(month_start.year, month_start.month + 1, 1, tzinfo=UTC)
