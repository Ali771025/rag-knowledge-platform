from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import Integer, Select, func, select
from sqlalchemy.orm import Session

from app.models.token_monitoring import APIKeyBudgetConfig, APIKeyMetadata, BudgetAlert, TokenUsageLog
from app.schemas.token_usage_analytics import (
    APIKeyUsageDetailsResponse,
    BudgetInfo,
    CostForecastResponse,
    ModelUsageMetrics,
    PaginatedRecentRequests,
    ProviderCostBreakdown,
    RecentRequestUsageItem,
    TokenUsageByModelResponse,
    TokenUsageSummaryPoint,
    TokenUsageSummaryResponse,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TokenUsageFilter:
    provider: str | None = None
    model: str | None = None
    api_key_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class TokenUsageAnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def summary(self, *, filters: TokenUsageFilter, granularity: str) -> TokenUsageSummaryResponse:
        rows = self._aggregate_rows(filters=filters, granularity=granularity)
        points = [
            TokenUsageSummaryPoint(
                bucket_start=self._coerce_bucket_start(row[0]),
                provider=str(row[1]),
                model_name=str(row[2]),
                api_key_id=row[3],
                total_cost_usd=Decimal(str(row[4] or Decimal("0"))),
                prompt_tokens=int(row[5] or 0),
                completion_tokens=int(row[6] or 0),
                total_tokens=int(row[7] or 0),
                request_count=int(row[8] or 0),
                avg_latency_ms=float(row[9] or 0.0),
                cache_hit_rate=float(row[10] or 0.0),
            )
            for row in rows
        ]

        breakdown_stmt = select(
            TokenUsageLog.provider,
            func.coalesce(func.sum(TokenUsageLog.cost_usd), Decimal("0")),
        ).group_by(TokenUsageLog.provider)
        breakdown_stmt = self._apply_filters(breakdown_stmt, filters)
        provider_cost_breakdown = [
            ProviderCostBreakdown(provider=str(row[0]), total_cost_usd=Decimal(str(row[1] or Decimal("0"))))
            for row in self.db.execute(breakdown_stmt).all()
        ]

        response = TokenUsageSummaryResponse(
            granularity=granularity,  # type: ignore[arg-type]
            points=points,
            provider_cost_breakdown=provider_cost_breakdown,
        )
        logger.debug(
            "token_usage.analytics_summary_generated",
            extra={
                "granularity": granularity,
                "point_count": len(response.points),
                "provider_filter": filters.provider,
                "model_filter": filters.model,
                "api_key_id_filter": str(filters.api_key_id) if filters.api_key_id else None,
            },
        )
        return response

    def by_model(self, *, filters: TokenUsageFilter) -> TokenUsageByModelResponse:
        stmt = select(
            TokenUsageLog.provider,
            TokenUsageLog.model_name,
            func.coalesce(func.sum(TokenUsageLog.prompt_tokens), 0),
            func.coalesce(func.sum(TokenUsageLog.completion_tokens), 0),
            func.coalesce(func.sum(TokenUsageLog.total_tokens), 0),
            func.coalesce(func.sum(TokenUsageLog.cost_usd), Decimal("0")),
            func.count(TokenUsageLog.id),
            func.coalesce(func.avg(TokenUsageLog.latency_ms), 0.0),
            func.coalesce(func.avg(func.cast(TokenUsageLog.cache_hit, Integer)), 0.0),
        ).group_by(TokenUsageLog.provider, TokenUsageLog.model_name)
        stmt = self._apply_filters(stmt, filters)

        items = [
            ModelUsageMetrics(
                provider=str(row[0]),
                model_name=str(row[1]),
                input_tokens=int(row[2] or 0),
                output_tokens=int(row[3] or 0),
                total_tokens=int(row[4] or 0),
                total_cost_usd=Decimal(str(row[5] or Decimal("0"))),
                request_count=int(row[6] or 0),
                avg_latency_ms=float(row[7] or 0.0),
                cache_hit_rate=float(row[8] or 0.0),
            )
            for row in self.db.execute(stmt).all()
        ]
        response = TokenUsageByModelResponse(items=items)
        logger.debug(
            "token_usage.analytics_by_model_generated",
            extra={
                "item_count": len(response.items),
                "provider_filter": filters.provider,
                "model_filter": filters.model,
                "api_key_id_filter": str(filters.api_key_id) if filters.api_key_id else None,
            },
        )
        return response

    def by_key(
        self,
        *,
        api_key_id: UUID,
        filters: TokenUsageFilter,
        granularity: str,
        page: int,
        page_size: int,
    ) -> APIKeyUsageDetailsResponse:
        api_key = self.db.get(APIKeyMetadata, api_key_id)
        if api_key is None:
            raise ValueError("API key not found")

        key_filters = TokenUsageFilter(
            provider=filters.provider,
            model=filters.model,
            api_key_id=api_key_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
        )
        summary = self.summary(filters=key_filters, granularity=granularity)

        recent_stmt = select(TokenUsageLog).where(TokenUsageLog.api_key_id == api_key_id)
        recent_stmt = self._apply_filters(recent_stmt, key_filters)
        total = int(self.db.scalar(select(func.count()).select_from(recent_stmt.subquery())) or 0)

        offset = (page - 1) * page_size
        rows = self.db.scalars(
            recent_stmt.order_by(TokenUsageLog.created_at.desc()).offset(offset).limit(page_size)
        ).all()
        items = [
            RecentRequestUsageItem(
                id=row.id,
                request_id=row.request_id,
                provider=row.provider,
                model_name=row.model_name,
                prompt_tokens=row.prompt_tokens,
                completion_tokens=row.completion_tokens,
                total_tokens=row.total_tokens,
                cost_usd=row.cost_usd,
                latency_ms=row.latency_ms,
                cache_hit=row.cache_hit,
                endpoint=row.endpoint,
                session_id=row.session_id,
                created_at=row.created_at,
            )
            for row in rows
        ]

        budget = None
        budget_config = self.db.scalar(select(APIKeyBudgetConfig).where(APIKeyBudgetConfig.api_key_id == api_key_id))
        latest_alert = self.db.scalar(
            select(BudgetAlert).where(BudgetAlert.api_key_id == api_key_id).order_by(BudgetAlert.triggered_at.desc())
        )
        if budget_config is not None:
            now = datetime.now(UTC)
            cycle_start = datetime(now.year, now.month, 1, tzinfo=UTC)
            current_spend = self.db.scalar(
                select(func.coalesce(func.sum(TokenUsageLog.cost_usd), Decimal("0"))).where(
                    TokenUsageLog.api_key_id == api_key_id,
                    TokenUsageLog.created_at >= cycle_start,
                    TokenUsageLog.created_at <= now,
                )
            )
            budget = BudgetInfo(
                current_spend_usd=Decimal(str(current_spend or Decimal("0"))),
                period="monthly",
                monthly_budget_usd=budget_config.monthly_budget_usd,
                alert_thresholds=list(budget_config.alert_thresholds_json or []),
            )
        elif latest_alert is not None:
            budget = BudgetInfo(current_spend_usd=latest_alert.current_spend_usd, period=latest_alert.period)

        response = APIKeyUsageDetailsResponse(
            api_key={
                "id": str(api_key.id),
                "provider": api_key.provider.value,
                "display_name": api_key.display_name,
                "key_alias": api_key.key_alias,
                "key_fingerprint": api_key.key_fingerprint,
                "is_active": api_key.is_active,
            },
            time_series=summary.points,
            recent_requests=PaginatedRecentRequests(
                page=page,
                page_size=page_size,
                total=total,
                items=items,
            ),
            budget=budget,
        )
        logger.debug(
            "token_usage.analytics_by_key_generated",
            extra={
                "api_key_id": str(api_key_id),
                "granularity": granularity,
                "time_series_points": len(response.time_series),
                "recent_request_count": len(response.recent_requests.items),
                "page": page,
                "page_size": page_size,
            },
        )
        return response

    def forecast(self, *, filters: TokenUsageFilter) -> CostForecastResponse:
        now = datetime.now(UTC)
        start = datetime(now.year, now.month, 1, tzinfo=UTC)
        if now.month == 12:
            period_end = date(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = date(now.year, now.month + 1, 1) - timedelta(days=1)

        stmt = select(
            func.coalesce(func.sum(TokenUsageLog.cost_usd), Decimal("0")),
            func.count(TokenUsageLog.id),
        ).where(TokenUsageLog.created_at >= start, TokenUsageLog.created_at <= now)
        stmt = self._apply_filters(stmt, filters)
        current_spend, request_count = self.db.execute(stmt).one()

        current_spend_dec = Decimal(str(current_spend or Decimal("0")))
        elapsed_days = max(now.day, 1)
        days_in_month = period_end.day

        projected = (current_spend_dec / Decimal(elapsed_days)) * Decimal(days_in_month)
        confidence = "high"
        confidence_note = "Sufficient signal from current period usage."
        if request_count < 10:
            confidence = "low"
            confidence_note = "Insufficient data points for a high-confidence forecast."
        elif request_count < 100:
            confidence = "medium"
            confidence_note = "Moderate sample size; projection may vary with traffic spikes."

        response = CostForecastResponse(
            current_spend_usd=current_spend_dec,
            projected_spend_usd=projected,
            confidence=confidence,
            confidence_note=confidence_note,
            period_start=start.date(),
            period_end=period_end,
        )
        logger.info(
            "token_usage.cost_forecast_generated",
            extra={
                "current_spend_usd": str(response.current_spend_usd),
                "projected_spend_usd": str(response.projected_spend_usd),
                "confidence": response.confidence,
                "provider_filter": filters.provider,
                "model_filter": filters.model,
                "api_key_id_filter": str(filters.api_key_id) if filters.api_key_id else None,
            },
        )
        return response

    def _aggregate_rows(self, *, filters: TokenUsageFilter, granularity: str):
        bucket_expr = self._bucket_expr(granularity)
        stmt = select(
            bucket_expr,
            TokenUsageLog.provider,
            TokenUsageLog.model_name,
            TokenUsageLog.api_key_id,
            func.coalesce(func.sum(TokenUsageLog.cost_usd), Decimal("0")),
            func.coalesce(func.sum(TokenUsageLog.prompt_tokens), 0),
            func.coalesce(func.sum(TokenUsageLog.completion_tokens), 0),
            func.coalesce(func.sum(TokenUsageLog.total_tokens), 0),
            func.count(TokenUsageLog.id),
            func.coalesce(func.avg(TokenUsageLog.latency_ms), 0.0),
            func.coalesce(func.avg(func.cast(TokenUsageLog.cache_hit, Integer)), 0.0),
        ).group_by(bucket_expr, TokenUsageLog.provider, TokenUsageLog.model_name, TokenUsageLog.api_key_id).order_by(bucket_expr.asc())
        stmt = self._apply_filters(stmt, filters)
        return self.db.execute(stmt).all()

    def _bucket_expr(self, granularity: str):
        dialect = self.db.bind.dialect.name if self.db.bind is not None else ""
        column = TokenUsageLog.created_at

        if dialect == "sqlite":
            if granularity == "hourly":
                return func.strftime("%Y-%m-%d %H:00:00", column)
            if granularity == "daily":
                return func.strftime("%Y-%m-%d 00:00:00", column)
            if granularity == "weekly":
                return func.date(column, "weekday 1", "-7 days")
            return func.strftime("%Y-%m-01 00:00:00", column)

        if granularity == "hourly":
            return func.date_trunc("hour", column)
        if granularity == "daily":
            return func.date_trunc("day", column)
        if granularity == "weekly":
            return func.date_trunc("week", column)
        return func.date_trunc("month", column)

    def _apply_filters(self, stmt: Select[Any], filters: TokenUsageFilter) -> Select[Any]:
        if filters.provider:
            stmt = stmt.where(TokenUsageLog.provider == filters.provider)
        if filters.model:
            stmt = stmt.where(TokenUsageLog.model_name == filters.model)
        if filters.api_key_id:
            stmt = stmt.where(TokenUsageLog.api_key_id == filters.api_key_id)
        if filters.date_from:
            stmt = stmt.where(TokenUsageLog.created_at >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(TokenUsageLog.created_at <= filters.date_to)
        return stmt


    @staticmethod
    def _coerce_bucket_start(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return datetime.now(UTC)
