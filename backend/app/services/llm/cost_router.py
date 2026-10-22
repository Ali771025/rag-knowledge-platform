"""Cost-aware model selection for routing decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.models.llm.contracts import ComplexityResult, LLMRequest, RoutingDecision
from app.services.llm.model_costs import ModelCost, list_model_costs

LatencyPreference = Literal["low", "balanced", "quality"]
BudgetMode = Literal["normal", "conservative", "aggressive_savings"]


@dataclass(slots=True)
class CostRouterConfig:
    """Configuration knobs for cost-aware model routing."""

    default_output_tokens: int = 256
    complexity_quality_floor_simple: int = 1
    complexity_quality_floor_medium: int = 2
    complexity_quality_floor_complex: int = 3
    complexity_quality_floor_high_risk: int = 4


class CostRouter:
    """Cheapest acceptable model selector using centralized pricing metadata."""

    def __init__(self, config: CostRouterConfig | None = None) -> None:
        self.config = config or CostRouterConfig()

    def select_optimal_model(
        self,
        complexity: ComplexityResult,
        estimated_input_tokens: int | None = None,
        estimated_output_tokens: int | None = None,
        latency_preference: LatencyPreference = "balanced",
        allowed_providers: list[str] | None = None,
        quality_floor: int | None = None,
        budget_mode: BudgetMode = "normal",
        candidate_models: list[str] | None = None,
    ) -> RoutingDecision:
        """Select the cheapest model that satisfies complexity and policy constraints."""
        prompt_tokens = estimated_input_tokens or complexity.estimated_input_tokens
        completion_tokens = estimated_output_tokens or self.config.default_output_tokens
        floors = self._resolve_quality_floor(complexity=complexity, quality_floor=quality_floor, budget_mode=budget_mode)

        candidates = self._load_candidates(
            allowed_providers=allowed_providers,
            candidate_models=candidate_models,
            minimum_quality=floors,
        )
        if not candidates:
            raise ValueError("No routing candidates satisfy the provider/model/quality constraints.")

        ranked = sorted(
            candidates,
            key=lambda item: self._ranking_key(
                item=item,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_preference=latency_preference,
            ),
        )
        selected = ranked[0]
        selected_cost = selected.estimate_cost_usd(prompt_tokens, completion_tokens)

        fallback_provider = None
        fallback_model = None
        if len(ranked) > 1:
            fallback_provider = ranked[1].provider
            fallback_model = ranked[1].model

        reason = (
            f"selected_cheapest_acceptable;"
            f" complexity={complexity.label};"
            f" quality_floor={floors};"
            f" latency_preference={latency_preference};"
            f" budget_mode={budget_mode}"
        )
        return RoutingDecision(
            provider=selected.provider,
            model=selected.model,
            reason=reason,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            estimated_cost_usd=selected_cost,
            complexity=complexity,
        )

    async def route(self, request: LLMRequest, complexity: ComplexityResult) -> RoutingDecision:
        """Backward-compatible route method using request metadata constraints."""
        metadata = request.metadata or {}
        allowed = metadata.get("allowed_providers")
        if not isinstance(allowed, list):
            allowed = None

        latency = metadata.get("latency_preference", "balanced")
        if latency not in ("low", "balanced", "quality"):
            latency = "balanced"

        quality_floor = metadata.get("quality_floor")
        if not isinstance(quality_floor, int):
            quality_floor = None

        budget_mode = metadata.get("budget_mode", "normal")
        if budget_mode not in ("normal", "conservative", "aggressive_savings"):
            budget_mode = "normal"

        return self.select_optimal_model(
            complexity=complexity,
            estimated_input_tokens=complexity.estimated_input_tokens,
            latency_preference=latency,
            allowed_providers=allowed,
            quality_floor=quality_floor,
            budget_mode=budget_mode,
            candidate_models=request.candidate_models or None,
        )

    def _resolve_quality_floor(
        self,
        complexity: ComplexityResult,
        quality_floor: int | None,
        budget_mode: BudgetMode,
    ) -> int:
        complexity_floor = {
            "simple": self.config.complexity_quality_floor_simple,
            "medium": self.config.complexity_quality_floor_medium,
            "complex": self.config.complexity_quality_floor_complex,
            "high_risk": self.config.complexity_quality_floor_high_risk,
        }[complexity.label]
        resolved = max(complexity_floor, quality_floor or 0)

        if budget_mode == "aggressive_savings":
            return max(1, resolved - 1)
        if budget_mode == "conservative":
            return resolved + 1
        return resolved

    @staticmethod
    def _load_candidates(
        allowed_providers: list[str] | None,
        candidate_models: list[str] | None,
        minimum_quality: int,
    ) -> list[ModelCost]:
        provider_set = {entry.lower().strip() for entry in allowed_providers or []}
        model_set = {entry.strip() for entry in candidate_models or []}
        costs = list_model_costs()
        result: list[ModelCost] = []
        for item in costs:
            if provider_set and item.provider not in provider_set:
                continue
            if model_set and item.model not in model_set:
                continue
            if item.quality_tier < minimum_quality:
                continue
            result.append(item)
        return result

    @staticmethod
    def _ranking_key(
        item: ModelCost,
        prompt_tokens: int,
        completion_tokens: int,
        latency_preference: LatencyPreference,
    ) -> tuple[float, int, int, str]:
        estimated_cost = item.estimate_cost_usd(prompt_tokens, completion_tokens)
        if latency_preference == "low":
            return (estimated_cost, item.latency_tier, -item.quality_tier, item.model)
        if latency_preference == "quality":
            return (estimated_cost, -item.quality_tier, item.latency_tier, item.model)
        return (estimated_cost, item.latency_tier, -item.quality_tier, item.model)
