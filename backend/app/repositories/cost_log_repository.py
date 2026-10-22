from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.cost_log import CostLog
from app.observability.repository_models import CostByPeriodAggregate, CostByStateAggregate


class CostLogRepository:
    """Data-access helpers for `cost_logs` records and cost aggregates."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **fields: Any) -> CostLog:
        log = CostLog(**fields)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def aggregate_cost_by_user_day(
        self,
        *,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        currency: str | None = None,
    ) -> list[CostByPeriodAggregate]:
        return self._aggregate_cost_by_user_period(
            user_id=user_id,
            period="day",
            start_date=start_date,
            end_date=end_date,
            currency=currency,
        )

    def aggregate_cost_by_user_month(
        self,
        *,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        currency: str | None = None,
    ) -> list[CostByPeriodAggregate]:
        return self._aggregate_cost_by_user_period(
            user_id=user_id,
            period="month",
            start_date=start_date,
            end_date=end_date,
            currency=currency,
        )

    def aggregate_cost_by_state(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        currency: str | None = None,
    ) -> list[CostByStateAggregate]:
        stmt = select(
            CostLog.state,
            CostLog.currency,
            func.coalesce(func.sum(CostLog.total_cost), Decimal("0")),
        ).group_by(CostLog.state, CostLog.currency)

        stmt = self._apply_datetime_filters(stmt=stmt, start_at=start_at, end_at=end_at)

        if currency is not None:
            stmt = stmt.where(CostLog.currency == currency.upper())

        stmt = stmt.order_by(CostLog.state.asc())

        rows = self.db.execute(stmt).all()
        return [
            CostByStateAggregate(
                state=row[0],
                currency=row[1],
                total_cost=Decimal(str(row[2] or Decimal("0"))),
            )
            for row in rows
        ]

    def aggregate_total_cost(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        currency: str | None = None,
    ) -> Decimal:
        stmt = select(func.coalesce(func.sum(CostLog.total_cost), Decimal("0")))
        stmt = self._apply_datetime_filters(stmt=stmt, start_at=start_at, end_at=end_at)

        if currency is not None:
            stmt = stmt.where(CostLog.currency == currency.upper())

        total = self.db.scalar(stmt)
        return Decimal(str(total or Decimal("0")))

    def aggregate_total_cost_by_user(
        self,
        *,
        user_id: UUID,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        currency: str | None = None,
    ) -> Decimal:
        stmt = select(func.coalesce(func.sum(CostLog.total_cost), Decimal("0"))).where(CostLog.user_id == user_id)
        stmt = self._apply_datetime_filters(stmt=stmt, start_at=start_at, end_at=end_at)

        if currency is not None:
            stmt = stmt.where(CostLog.currency == currency.upper())

        total = self.db.scalar(stmt)
        return Decimal(str(total or Decimal("0")))

    def aggregate_total_cost_for_state(
        self,
        *,
        state: str,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        currency: str | None = None,
    ) -> Decimal:
        stmt = select(func.coalesce(func.sum(CostLog.total_cost), Decimal("0"))).where(CostLog.state == state)
        stmt = self._apply_datetime_filters(stmt=stmt, start_at=start_at, end_at=end_at)

        if currency is not None:
            stmt = stmt.where(CostLog.currency == currency.upper())

        total = self.db.scalar(stmt)
        return Decimal(str(total or Decimal("0")))

    def aggregate_total_tokens(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        currency: str | None = None,
    ) -> int:
        stmt = select(func.coalesce(func.sum(CostLog.total_tokens), 0))
        stmt = self._apply_datetime_filters(stmt=stmt, start_at=start_at, end_at=end_at)

        if currency is not None:
            stmt = stmt.where(CostLog.currency == currency.upper())

        total = self.db.scalar(stmt)
        return int(total or 0)

    def _aggregate_cost_by_user_period(
        self,
        *,
        user_id: UUID,
        period: Literal["day", "month"],
        start_date: date | None,
        end_date: date | None,
        currency: str | None,
    ) -> list[CostByPeriodAggregate]:
        period_label = self._period_bucket(period).label("period_start")

        stmt = (
            select(
                period_label,
                CostLog.currency,
                func.coalesce(func.sum(CostLog.total_cost), Decimal("0")),
            )
            .where(CostLog.user_id == user_id)
            .group_by(period_label, CostLog.currency)
            .order_by(period_label.asc())
        )

        if currency is not None:
            stmt = stmt.where(CostLog.currency == currency.upper())

        if start_date is not None:
            start_at = datetime(start_date.year, start_date.month, start_date.day, tzinfo=UTC)
            stmt = stmt.where(CostLog.created_at >= start_at)

        if end_date is not None:
            end_at = datetime(end_date.year, end_date.month, end_date.day, tzinfo=UTC) + timedelta(days=1)
            stmt = stmt.where(CostLog.created_at < end_at)

        rows = self.db.execute(stmt).all()
        return [
            CostByPeriodAggregate(
                period_start=self._coerce_period_start(row[0]),
                currency=row[1],
                total_cost=Decimal(str(row[2] or Decimal("0"))),
            )
            for row in rows
        ]

    def _period_bucket(self, period: Literal["day", "month"]) -> Any:
        dialect_name = self.db.bind.dialect.name if self.db.bind is not None else ""
        if period == "day":
            return func.date(CostLog.created_at)

        if dialect_name == "sqlite":
            return func.strftime("%Y-%m-01", CostLog.created_at)

        return func.date_trunc("month", CostLog.created_at)

    def _coerce_period_start(self, raw_value: Any) -> date:
        if isinstance(raw_value, datetime):
            return raw_value.date()
        if isinstance(raw_value, date):
            return raw_value
        if isinstance(raw_value, str):
            try:
                return date.fromisoformat(raw_value)
            except ValueError:
                # Covers date_trunc string shapes with a timestamp component.
                return datetime.fromisoformat(raw_value).date()
        raise TypeError(f"Unsupported grouped period type: {type(raw_value)!r}")

    def _apply_datetime_filters(
        self,
        *,
        stmt: Select[tuple[Any, ...]],
        start_at: datetime | None,
        end_at: datetime | None,
    ) -> Select[tuple[Any, ...]]:
        if start_at is not None:
            stmt = stmt.where(CostLog.created_at >= start_at)
        if end_at is not None:
            stmt = stmt.where(CostLog.created_at < end_at)
        return stmt
