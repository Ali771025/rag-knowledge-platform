from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BudgetUpdateRequest(BaseModel):
    monthly_budget_usd: Decimal | None = Field(default=None)
    alert_thresholds: list[int] = Field(default_factory=lambda: [80, 90, 100])

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    @field_validator("monthly_budget_usd")
    @classmethod
    def validate_monthly_budget(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if value <= Decimal("0"):
            raise ValueError("monthly_budget_usd must be greater than zero")
        return value

    @field_validator("alert_thresholds")
    @classmethod
    def validate_thresholds(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("alert_thresholds must not be empty")
        if value != sorted(value):
            raise ValueError("alert_thresholds must be sorted in ascending order")
        if len(set(value)) != len(value):
            raise ValueError("alert_thresholds must contain unique values")
        for threshold in value:
            if threshold < 1 or threshold > 100:
                raise ValueError("alert_thresholds must be integers between 1 and 100")
        return value


class APIKeyBudgetConfigResponse(BaseModel):
    api_key_id: UUID
    monthly_budget_usd: Decimal | None
    alert_thresholds: list[int]
    updated_at: datetime

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class ActiveBudgetAlertItem(BaseModel):
    id: UUID
    api_key_id: UUID
    key_alias: str | None
    provider: str
    threshold_percent: int
    threshold_usd: Decimal
    current_spend_usd: Decimal
    budget_usd: Decimal | None
    triggered_at: datetime
    status: str
    cycle_start: date | None
    cycle_end: date | None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class ActiveBudgetAlertsResponse(BaseModel):
    items: list[ActiveBudgetAlertItem]

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class APIKeyListItem(BaseModel):
    id: UUID
    display_name: str
    key_alias: str | None
    provider: str
    is_active: bool
    key_fingerprint: str
    monthly_budget_usd: Decimal | None
    alert_thresholds: list[int]
    current_month_spend_usd: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    last_used_at: datetime | None = None

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class APIKeyListResponse(BaseModel):
    items: list[APIKeyListItem]

    model_config = ConfigDict(extra="forbid", protected_namespaces=())
