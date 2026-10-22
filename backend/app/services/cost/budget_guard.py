"""Budget protection rules for warning, restriction, and emergency downgrade modes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.llm.contracts import CostSummarySnapshot

BudgetMode = Literal["normal", "warning", "restrictive", "emergency"]


@dataclass(slots=True)
class BudgetThresholds:
    """Configuration-driven budget thresholds for daily and monthly windows."""

    daily_warning_usd: float = 10.0
    daily_restrictive_usd: float = 20.0
    daily_emergency_usd: float = 40.0
    monthly_warning_usd: float = 200.0
    monthly_restrictive_usd: float = 400.0
    monthly_emergency_usd: float = 800.0


@dataclass(slots=True)
class BudgetGuardConfig:
    """Policy toggles for degradation controls at different budget modes."""

    thresholds: BudgetThresholds = field(default_factory=BudgetThresholds)
    disable_non_critical_expensive_paths_in_warning: bool = False
    disable_non_critical_expensive_paths_in_restrictive: bool = True
    disable_non_critical_expensive_paths_in_emergency: bool = True
    force_downgrade_quality_tier_in_warning: int = 0
    force_downgrade_quality_tier_in_restrictive: int = 1
    force_downgrade_quality_tier_in_emergency: int = 2


class BudgetDecision(BaseModel):
    """Typed budget decision for routing and orchestration consumers."""

    mode: BudgetMode
    within_budget: bool
    spend_ratio_daily: float = Field(..., ge=0.0)
    spend_ratio_monthly: float = Field(..., ge=0.0)
    should_downgrade_model_class: bool
    quality_tier_downgrade_steps: int = Field(default=0, ge=0)
    disable_non_critical_expensive_paths: bool
    allow_provider_calls: bool = True
    reason: str = Field(..., min_length=1, max_length=512)

    model_config = ConfigDict(extra="forbid")


class BudgetGuard:
    """Deterministic budget policy evaluator with no hidden dependencies."""

    def __init__(self, config: BudgetGuardConfig | None = None) -> None:
        self.config = config or BudgetGuardConfig()

    async def evaluate_budget(
        self,
        *,
        daily_snapshot: CostSummarySnapshot,
        monthly_snapshot: CostSummarySnapshot,
    ) -> BudgetDecision:
        """Evaluate daily/monthly spend and return a structured protection decision."""
        thresholds = self.config.thresholds
        daily_spend = max(float(daily_snapshot.total_estimated_cost_usd), 0.0)
        monthly_spend = max(float(monthly_snapshot.total_estimated_cost_usd), 0.0)

        daily_mode = self._mode_from_spend(
            spend=daily_spend,
            warning=thresholds.daily_warning_usd,
            restrictive=thresholds.daily_restrictive_usd,
            emergency=thresholds.daily_emergency_usd,
        )
        monthly_mode = self._mode_from_spend(
            spend=monthly_spend,
            warning=thresholds.monthly_warning_usd,
            restrictive=thresholds.monthly_restrictive_usd,
            emergency=thresholds.monthly_emergency_usd,
        )
        mode = self._max_mode(daily_mode, monthly_mode)

        if mode == "warning":
            downgrade_steps = self.config.force_downgrade_quality_tier_in_warning
            disable_expensive = self.config.disable_non_critical_expensive_paths_in_warning
        elif mode == "restrictive":
            downgrade_steps = self.config.force_downgrade_quality_tier_in_restrictive
            disable_expensive = self.config.disable_non_critical_expensive_paths_in_restrictive
        elif mode == "emergency":
            downgrade_steps = self.config.force_downgrade_quality_tier_in_emergency
            disable_expensive = self.config.disable_non_critical_expensive_paths_in_emergency
        else:
            downgrade_steps = 0
            disable_expensive = False

        should_downgrade = downgrade_steps > 0
        allow_provider_calls = mode != "emergency"

        return BudgetDecision(
            mode=mode,
            within_budget=mode == "normal",
            spend_ratio_daily=self._safe_ratio(daily_spend, thresholds.daily_warning_usd),
            spend_ratio_monthly=self._safe_ratio(monthly_spend, thresholds.monthly_warning_usd),
            should_downgrade_model_class=should_downgrade,
            quality_tier_downgrade_steps=downgrade_steps,
            disable_non_critical_expensive_paths=disable_expensive,
            allow_provider_calls=allow_provider_calls,
            reason=(
                f"budget_mode={mode};"
                f" daily_spend={daily_spend:.4f};"
                f" monthly_spend={monthly_spend:.4f}"
            ),
        )

    async def is_within_budget(self, snapshot: CostSummarySnapshot) -> bool:
        """Backward-compatible budget boolean check using daily snapshot only."""
        decision = await self.evaluate_budget(daily_snapshot=snapshot, monthly_snapshot=snapshot)
        return decision.within_budget

    @staticmethod
    def _mode_from_spend(spend: float, warning: float, restrictive: float, emergency: float) -> BudgetMode:
        if spend >= emergency:
            return "emergency"
        if spend >= restrictive:
            return "restrictive"
        if spend >= warning:
            return "warning"
        return "normal"

    @staticmethod
    def _max_mode(first: BudgetMode, second: BudgetMode) -> BudgetMode:
        order = {"normal": 0, "warning": 1, "restrictive": 2, "emergency": 3}
        return first if order[first] >= order[second] else second

    @staticmethod
    def _safe_ratio(numerator: float, denominator: float) -> float:
        if denominator <= 0:
            return 0.0
        return round(numerator / denominator, 4)
