from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from app.models.token_monitoring import (
    APIKeyBudgetConfig,
    APIKeyMetadata,
    OptimizationRecommendation,
    RecommendationCategory,
    RecommendationSeverity,
    TokenProvider,
    TokenUsageLog,
)
from app.repositories.token_monitoring_repository import OptimizationRecommendationRepository
from app.services.token_monitoring import TokenPricingEngine

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RecommendationCandidate:
    api_key_id: UUID | None
    category: RecommendationCategory
    severity: RecommendationSeverity
    title: str
    description: str
    potential_saving_usd: Decimal
    action_items: list[str]
    payload: dict[str, Any]
    dedupe_key: str


class TokenOptimizationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = OptimizationRecommendationRepository(db)
        self.pricing = TokenPricingEngine()

    def generate_recommendations(self, *, now: datetime | None = None) -> list[OptimizationRecommendation]:
        created_at = now or datetime.now(UTC)
        lookback_start = created_at - timedelta(days=30)

        candidates: list[RecommendationCandidate] = []
        candidates.extend(self._model_downgrade_candidates(lookback_start=lookback_start))
        candidates.extend(self._caching_candidates(lookback_start=lookback_start))
        candidates.extend(self._token_waste_candidates(lookback_start=lookback_start))
        candidates.extend(self._rate_limit_candidates(lookback_start=lookback_start))
        candidates.extend(self._provider_arbitrage_candidates(lookback_start=lookback_start))
        candidates.extend(self._budget_risk_candidates(now=created_at))

        created: list[OptimizationRecommendation] = []
        dedupe_window = created_at - timedelta(days=7)

        for candidate in candidates:
            if self.repo.exists_recent_dedupe(dedupe_key=candidate.dedupe_key, created_after=dedupe_window):
                continue

            rec = OptimizationRecommendation(
                api_key_id=candidate.api_key_id,
                category=candidate.category,
                severity=candidate.severity,
                title=candidate.title,
                summary=candidate.description,
                description=candidate.description,
                potential_saving_usd=max(candidate.potential_saving_usd, Decimal("0")),
                action_items_json=candidate.action_items,
                payload_json=candidate.payload,
                dedupe_key=candidate.dedupe_key,
                generated_at=created_at,
                is_dismissed=False,
            )
            created.append(self.repo.create(rec))

        logger.info(
            "token_optimization.recommendations_generated",
            extra={
                "candidate_count": len(candidates),
                "created_count": len(created),
                "generated_at": created_at.isoformat(),
            },
        )
        return created

    def list_recommendations(self, *, include_dismissed: bool = False, limit: int = 200) -> list[OptimizationRecommendation]:
        return self.repo.list_recommendations(include_dismissed=include_dismissed, limit=limit)

    def dismiss_recommendation(self, recommendation_id: UUID) -> OptimizationRecommendation:
        recommendation = self.repo.get_by_id(recommendation_id)
        if recommendation is None:
            raise ValueError("Recommendation not found")
        if recommendation.is_dismissed:
            return recommendation
        return self.repo.dismiss(recommendation)

    def savings_report(self) -> tuple[Decimal, dict[RecommendationCategory, Decimal], int]:
        recommendations = self.repo.list_recommendations(include_dismissed=False, limit=10_000)
        total = Decimal("0")
        by_category: dict[RecommendationCategory, Decimal] = {}
        high_priority = 0

        for recommendation in recommendations:
            saving = Decimal(str(recommendation.potential_saving_usd or Decimal("0")))
            total += saving
            by_category[recommendation.category] = by_category.get(recommendation.category, Decimal("0")) + saving
            if recommendation.severity in {RecommendationSeverity.WARNING, RecommendationSeverity.CRITICAL}:
                high_priority += 1

        return total, by_category, high_priority

    def _model_downgrade_candidates(self, *, lookback_start: datetime) -> list[RecommendationCandidate]:
        downgrade_map: dict[tuple[str, str], str] = {
            (TokenProvider.OPENAI.value, "gpt-4o"): "gpt-4o-mini",
            (TokenProvider.ANTHROPIC.value, "claude-3-5-sonnet-latest"): "claude-3-5-haiku-latest",
            (TokenProvider.DEEPSEEK.value, "deepseek-reasoner"): "deepseek-chat",
        }
        stmt = (
            select(
                TokenUsageLog.api_key_id,
                TokenUsageLog.provider,
                TokenUsageLog.model_name,
                func.coalesce(TokenUsageLog.endpoint, "unknown"),
                func.avg(TokenUsageLog.total_tokens),
                func.count(TokenUsageLog.id),
                func.sum(TokenUsageLog.prompt_tokens),
                func.sum(TokenUsageLog.completion_tokens),
            )
            .where(TokenUsageLog.created_at >= lookback_start)
            .group_by(
                TokenUsageLog.api_key_id,
                TokenUsageLog.provider,
                TokenUsageLog.model_name,
                func.coalesce(TokenUsageLog.endpoint, "unknown"),
            )
        )

        items: list[RecommendationCandidate] = []
        for row in self.db.execute(stmt).all():
            api_key_id, provider, model_name, endpoint, avg_total_tokens, request_count, prompt_sum, completion_sum = row
            provider_value = provider.value if hasattr(provider, "value") else str(provider)
            fallback_model = downgrade_map.get((provider_value, str(model_name)))
            if fallback_model is None:
                continue
            if float(avg_total_tokens or 0.0) >= 500 or int(request_count or 0) < 20:
                continue

            current_cost = self.pricing.calculate_cost(
                provider=provider_value,
                model_name=str(model_name),
                prompt_tokens=int(prompt_sum or 0),
                completion_tokens=int(completion_sum or 0),
            )
            cheaper_cost = self.pricing.calculate_cost(
                provider=provider_value,
                model_name=fallback_model,
                prompt_tokens=int(prompt_sum or 0),
                completion_tokens=int(completion_sum or 0),
            )
            potential_saving = max(current_cost.cost_usd - cheaper_cost.cost_usd, Decimal("0"))
            if potential_saving <= Decimal("0"):
                continue

            severity = RecommendationSeverity.WARNING if potential_saving >= Decimal("1") else RecommendationSeverity.INFO
            dedupe_key = f"downgrade:{api_key_id}:{provider_value}:{model_name}:{endpoint}"

            items.append(
                RecommendationCandidate(
                    api_key_id=api_key_id,
                    category=RecommendationCategory.COST,
                    severity=severity,
                    title=f"Consider downgrading {model_name} on {endpoint}",
                    description=(
                        f"Low-token traffic on {endpoint} is using {model_name}. "
                        f"Switching to {fallback_model} can reduce spend with limited quality impact."
                    ),
                    potential_saving_usd=potential_saving,
                    action_items=[
                        f"Review endpoint routing for {endpoint}.",
                        f"A/B test {fallback_model} for 10% of traffic.",
                    ],
                    payload={
                        "provider": provider_value,
                        "model_name": str(model_name),
                        "fallback_model": fallback_model,
                        "endpoint": endpoint,
                        "request_count": int(request_count or 0),
                        "avg_total_tokens": float(avg_total_tokens or 0.0),
                    },
                    dedupe_key=dedupe_key,
                )
            )

        return items

    def _caching_candidates(self, *, lookback_start: datetime) -> list[RecommendationCandidate]:
        stmt = (
            select(
                TokenUsageLog.api_key_id,
                TokenUsageLog.provider,
                func.coalesce(TokenUsageLog.endpoint, "unknown"),
                func.count(TokenUsageLog.id),
                func.coalesce(func.avg(func.cast(TokenUsageLog.cache_hit, Integer)), 0.0),
                func.coalesce(func.sum(TokenUsageLog.cost_usd), Decimal("0")),
            )
            .where(TokenUsageLog.created_at >= lookback_start)
            .group_by(
                TokenUsageLog.api_key_id,
                TokenUsageLog.provider,
                func.coalesce(TokenUsageLog.endpoint, "unknown"),
            )
        )

        items: list[RecommendationCandidate] = []
        for row in self.db.execute(stmt).all():
            api_key_id, provider, endpoint, request_count, cache_hit_rate, total_cost = row
            if int(request_count or 0) < 30 or float(cache_hit_rate or 0.0) >= 0.2:
                continue

            provider_value = provider.value if hasattr(provider, "value") else str(provider)
            potential_saving = (Decimal(str(total_cost or Decimal("0"))) * Decimal("0.2")).quantize(Decimal("0.000000001"))
            dedupe_key = f"cache:{api_key_id}:{provider_value}:{endpoint}"

            items.append(
                RecommendationCandidate(
                    api_key_id=api_key_id,
                    category=RecommendationCategory.CACHING,
                    severity=RecommendationSeverity.WARNING,
                    title=f"Increase cache reuse on {endpoint}",
                    description=(
                        f"Cache hit rate is {float(cache_hit_rate or 0.0):.1%} across {int(request_count)} requests. "
                        "Prompt normalization and cache key strategy can lower repeated-token spend."
                    ),
                    potential_saving_usd=potential_saving,
                    action_items=[
                        "Normalize dynamic prompt fragments before cache lookup.",
                        "Increase semantic cache TTL for repeat-heavy endpoints.",
                    ],
                    payload={
                        "provider": provider_value,
                        "endpoint": endpoint,
                        "request_count": int(request_count),
                        "cache_hit_rate": float(cache_hit_rate or 0.0),
                    },
                    dedupe_key=dedupe_key,
                )
            )

        return items

    def _token_waste_candidates(self, *, lookback_start: datetime) -> list[RecommendationCandidate]:
        stmt = (
            select(
                TokenUsageLog.api_key_id,
                TokenUsageLog.provider,
                func.coalesce(TokenUsageLog.endpoint, "unknown"),
                func.count(TokenUsageLog.id),
                func.coalesce(func.avg(TokenUsageLog.prompt_tokens), 0.0),
                func.coalesce(func.avg(TokenUsageLog.completion_tokens), 0.0),
                func.coalesce(func.sum(TokenUsageLog.cost_usd), Decimal("0")),
            )
            .where(TokenUsageLog.created_at >= lookback_start)
            .group_by(
                TokenUsageLog.api_key_id,
                TokenUsageLog.provider,
                func.coalesce(TokenUsageLog.endpoint, "unknown"),
            )
        )

        items: list[RecommendationCandidate] = []
        for row in self.db.execute(stmt).all():
            api_key_id, provider, endpoint, request_count, avg_prompt, avg_completion, total_cost = row
            prompt_avg = float(avg_prompt or 0.0)
            completion_avg = float(avg_completion or 0.0)
            if int(request_count or 0) < 20:
                continue
            if prompt_avg < 500 or completion_avg <= 0:
                continue
            if prompt_avg < completion_avg * 4:
                continue

            provider_value = provider.value if hasattr(provider, "value") else str(provider)
            potential_saving = (Decimal(str(total_cost or Decimal("0"))) * Decimal("0.15")).quantize(Decimal("0.000000001"))
            dedupe_key = f"token_waste:{api_key_id}:{provider_value}:{endpoint}"

            items.append(
                RecommendationCandidate(
                    api_key_id=api_key_id,
                    category=RecommendationCategory.PERFORMANCE,
                    severity=RecommendationSeverity.WARNING,
                    title=f"Reduce prompt overhead on {endpoint}",
                    description=(
                        f"Average prompt tokens ({prompt_avg:.0f}) are much higher than completion tokens ({completion_avg:.0f}). "
                        "Prompt compression can lower latency and cost."
                    ),
                    potential_saving_usd=potential_saving,
                    action_items=[
                        "Trim repeated context blocks.",
                        "Move static instructions to system-level templates.",
                    ],
                    payload={
                        "provider": provider_value,
                        "endpoint": endpoint,
                        "request_count": int(request_count),
                        "avg_prompt_tokens": prompt_avg,
                        "avg_completion_tokens": completion_avg,
                    },
                    dedupe_key=dedupe_key,
                )
            )

        return items

    def _rate_limit_candidates(self, *, lookback_start: datetime) -> list[RecommendationCandidate]:
        api_keys = self.db.scalars(select(APIKeyMetadata)).all()
        items: list[RecommendationCandidate] = []

        for api_key in api_keys:
            rate_limit_tpm = int((api_key.metadata_json or {}).get("rate_limit_tpm", 0) or 0)
            if rate_limit_tpm <= 0:
                continue

            minute_bucket = func.date_trunc("minute", TokenUsageLog.created_at)
            if self.db.bind is not None and self.db.bind.dialect.name == "sqlite":
                minute_bucket = func.strftime("%Y-%m-%d %H:%M:00", TokenUsageLog.created_at)

            peak_stmt = (
                select(func.coalesce(func.sum(TokenUsageLog.total_tokens), 0))
                .where(
                    TokenUsageLog.api_key_id == api_key.id,
                    TokenUsageLog.created_at >= lookback_start,
                )
                .group_by(minute_bucket)
            )
            peaks = [int(value or 0) for value in self.db.scalars(peak_stmt).all()]
            peak_tokens = max(peaks) if peaks else 0
            if peak_tokens < int(rate_limit_tpm * 0.8):
                continue

            utilization = float(peak_tokens) / float(rate_limit_tpm)
            dedupe_key = f"rate_limit:{api_key.id}:{rate_limit_tpm}"
            items.append(
                RecommendationCandidate(
                    api_key_id=api_key.id,
                    category=RecommendationCategory.RELIABILITY,
                    severity=RecommendationSeverity.WARNING,
                    title=f"API key {api_key.display_name} nears TPM limit",
                    description=(
                        f"Peak minute usage reached {peak_tokens} tokens against a {rate_limit_tpm} TPM limit "
                        f"({utilization:.0%} utilization)."
                    ),
                    potential_saving_usd=Decimal("0"),
                    action_items=[
                        "Distribute load across additional API keys.",
                        "Queue bursty workloads to smooth token throughput.",
                    ],
                    payload={
                        "rate_limit_tpm": rate_limit_tpm,
                        "peak_tokens_per_minute": peak_tokens,
                        "utilization": utilization,
                    },
                    dedupe_key=dedupe_key,
                )
            )

        return items

    def _provider_arbitrage_candidates(self, *, lookback_start: datetime) -> list[RecommendationCandidate]:
        stmt = (
            select(
                TokenUsageLog.api_key_id,
                TokenUsageLog.provider,
                TokenUsageLog.model_name,
                func.coalesce(TokenUsageLog.endpoint, "unknown"),
                func.count(TokenUsageLog.id),
                func.coalesce(func.avg(TokenUsageLog.prompt_tokens), 0.0),
                func.coalesce(func.avg(TokenUsageLog.completion_tokens), 0.0),
            )
            .where(TokenUsageLog.created_at >= lookback_start)
            .group_by(
                TokenUsageLog.api_key_id,
                TokenUsageLog.provider,
                TokenUsageLog.model_name,
                func.coalesce(TokenUsageLog.endpoint, "unknown"),
            )
        )

        alternatives: tuple[tuple[str, str], ...] = (
            (TokenProvider.DEEPSEEK.value, "deepseek-chat"),
            (TokenProvider.OPENAI.value, "gpt-4o-mini"),
            (TokenProvider.ANTHROPIC.value, "claude-3-5-haiku-latest"),
        )

        items: list[RecommendationCandidate] = []
        for row in self.db.execute(stmt).all():
            api_key_id, provider, model_name, endpoint, request_count, avg_prompt, avg_completion = row
            if int(request_count or 0) < 25:
                continue

            provider_value = provider.value if hasattr(provider, "value") else str(provider)
            prompt_tokens = int(float(avg_prompt or 0.0))
            completion_tokens = int(float(avg_completion or 0.0))
            current = self.pricing.calculate_cost(
                provider=provider_value,
                model_name=str(model_name),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
            if not current.pricing_found:
                continue

            best_provider = provider_value
            best_model = str(model_name)
            best_cost = current.cost_usd
            for candidate_provider, candidate_model in alternatives:
                alternative = self.pricing.calculate_cost(
                    provider=candidate_provider,
                    model_name=candidate_model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
                if not alternative.pricing_found:
                    continue
                if alternative.cost_usd < best_cost:
                    best_provider = candidate_provider
                    best_model = candidate_model
                    best_cost = alternative.cost_usd

            if best_model == str(model_name):
                continue

            projected_saving = (current.cost_usd - best_cost) * Decimal(int(request_count or 0))
            if projected_saving <= Decimal("0"):
                continue

            dedupe_key = f"arbitrage:{api_key_id}:{provider_value}:{model_name}:{endpoint}:{best_provider}:{best_model}"
            items.append(
                RecommendationCandidate(
                    api_key_id=api_key_id,
                    category=RecommendationCategory.COST,
                    severity=RecommendationSeverity.INFO,
                    title=f"Evaluate provider arbitrage for {endpoint}",
                    description=(
                        f"Current {provider_value}/{model_name} traffic may be cheaper on {best_provider}/{best_model} "
                        "for similar token patterns."
                    ),
                    potential_saving_usd=projected_saving.quantize(Decimal("0.000000001")),
                    action_items=[
                        "Benchmark output quality across both provider/model options.",
                        "Route 5-10% shadow traffic to validate quality and latency.",
                    ],
                    payload={
                        "current_provider": provider_value,
                        "current_model": str(model_name),
                        "candidate_provider": best_provider,
                        "candidate_model": best_model,
                        "endpoint": endpoint,
                        "request_count": int(request_count),
                    },
                    dedupe_key=dedupe_key,
                )
            )

        return items

    def _budget_risk_candidates(self, *, now: datetime) -> list[RecommendationCandidate]:
        month_start = datetime(now.year, now.month, 1, tzinfo=UTC)
        days_elapsed = max(now.day, 1)

        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1, tzinfo=UTC)
        else:
            next_month = datetime(now.year, now.month + 1, 1, tzinfo=UTC)
        days_in_month = (next_month.date() - month_start.date()).days

        configs = self.db.scalars(select(APIKeyBudgetConfig).where(APIKeyBudgetConfig.monthly_budget_usd.is_not(None))).all()

        items: list[RecommendationCandidate] = []
        for config in configs:
            if config.monthly_budget_usd is None or config.monthly_budget_usd <= Decimal("0"):
                continue

            spend_stmt = select(func.coalesce(func.sum(TokenUsageLog.cost_usd), Decimal("0"))).where(
                TokenUsageLog.api_key_id == config.api_key_id,
                TokenUsageLog.created_at >= month_start,
                TokenUsageLog.created_at < now,
            )
            current_spend = Decimal(str(self.db.scalar(spend_stmt) or Decimal("0")))
            projected = (current_spend / Decimal(days_elapsed)) * Decimal(days_in_month)
            if projected <= config.monthly_budget_usd:
                continue

            overage = projected - config.monthly_budget_usd
            ratio = projected / config.monthly_budget_usd if config.monthly_budget_usd > 0 else Decimal("0")
            severity = RecommendationSeverity.CRITICAL if ratio >= Decimal("1.2") else RecommendationSeverity.WARNING

            dedupe_key = f"budget_risk:{config.api_key_id}:{month_start.date().isoformat()}"
            items.append(
                RecommendationCandidate(
                    api_key_id=config.api_key_id,
                    category=RecommendationCategory.COST,
                    severity=severity,
                    title="Projected monthly spend exceeds configured budget",
                    description=(
                        f"Projected spend is ${projected:.4f} vs budget ${config.monthly_budget_usd:.4f}. "
                        "Apply routing/caching optimizations to avoid overage."
                    ),
                    potential_saving_usd=overage.quantize(Decimal("0.000000001")),
                    action_items=[
                        "Apply cheaper model routes on low-complexity traffic.",
                        "Increase cache coverage on repeat requests.",
                    ],
                    payload={
                        "current_spend_usd": str(current_spend),
                        "projected_spend_usd": str(projected),
                        "budget_usd": str(config.monthly_budget_usd),
                    },
                    dedupe_key=dedupe_key,
                )
            )

        return items
