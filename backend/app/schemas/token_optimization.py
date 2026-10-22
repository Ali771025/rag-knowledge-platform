from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.token_monitoring import RecommendationCategory, RecommendationSeverity


class OptimizationRecommendationItem(BaseModel):
    id: UUID
    api_key_id: UUID | None
    category: RecommendationCategory
    severity: RecommendationSeverity
    title: str
    description: str
    potential_saving_usd: Decimal = Field(ge=Decimal("0"))
    action_items: list[str] = Field(default_factory=list)
    generated_at: datetime
    is_dismissed: bool
    dismissed_at: datetime | None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class OptimizationRecommendationListResponse(BaseModel):
    items: list[OptimizationRecommendationItem]

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class RecommendationDismissResponse(BaseModel):
    id: UUID
    is_dismissed: bool
    dismissed_at: datetime | None

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class SavingsByCategory(BaseModel):
    category: RecommendationCategory
    potential_saving_usd: Decimal = Field(ge=Decimal("0"))

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class OptimizationSavingsReportResponse(BaseModel):
    total_potential_monthly_savings_usd: Decimal = Field(ge=Decimal("0"))
    savings_by_category: list[SavingsByCategory]
    high_priority_recommendation_count: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid", protected_namespaces=())
