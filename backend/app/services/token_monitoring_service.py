from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.models.token_monitoring import (
    APIKeyMetadata,
    BudgetAlert,
    OptimizationRecommendation,
    TokenProvider,
)
from app.repositories.token_monitoring_repository import (
    APIKeyRepository,
    BudgetAlertRepository,
    DailyAggregateRepository,
    OptimizationRecommendationRepository,
    TokenUsageLogRepository,
)
from app.services.token_monitoring import APIKeyHasher, TokenPricingEngine


class TokenMonitoringService:
    def __init__(
        self,
        *,
        api_keys: APIKeyRepository,
        usage_logs: TokenUsageLogRepository,
        daily_aggregates: DailyAggregateRepository,
        recommendations: OptimizationRecommendationRepository,
        budget_alerts: BudgetAlertRepository,
        pricing_engine: TokenPricingEngine | None = None,
    ) -> None:
        self.api_keys = api_keys
        self.usage_logs = usage_logs
        self.daily_aggregates = daily_aggregates
        self.recommendations = recommendations
        self.budget_alerts = budget_alerts
        self.pricing_engine = pricing_engine or TokenPricingEngine()

    def register_api_key(self, *, provider: TokenProvider, display_name: str, raw_key: str) -> APIKeyMetadata:
        hashed = APIKeyHasher.hash_key(raw_key)
        return self.api_keys.create(
            provider=provider,
            display_name=display_name,
            key_alias=hashed.key_alias,
            key_fingerprint=hashed.key_fingerprint,
            key_hash=hashed.key_hash,
        )

    def record_usage(
        self,
        *,
        api_key_id: UUID,
        provider: TokenProvider,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        request_id: str | None = None,
    ):
        pricing = self.pricing_engine.calculate_cost(
            provider=provider,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        return self.usage_logs.create(
            api_key_id=api_key_id,
            provider=provider,
            model_name=model_name,
            prompt_tokens=pricing.prompt_tokens,
            completion_tokens=pricing.completion_tokens,
            total_tokens=pricing.total_tokens,
            cost_usd=pricing.cost_usd,
            request_id=request_id,
        )

    def get_daily_cost_total(self, *, api_key_id: UUID, start_date: date | None = None, end_date: date | None = None) -> Decimal:
        return self.daily_aggregates.aggregate_cost(
            api_key_id=api_key_id,
            start_date=start_date,
            end_date=end_date,
        )

    def save_recommendation(self, recommendation: OptimizationRecommendation) -> OptimizationRecommendation:
        return self.recommendations.create(recommendation)

    def save_budget_alert(self, alert: BudgetAlert) -> BudgetAlert:
        return self.budget_alerts.create(alert)


__all__ = ["TokenMonitoringService"]
