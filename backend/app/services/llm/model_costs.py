"""Centralized model pricing configuration for LLM routing and cost estimation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ProviderName = Literal["deepseek", "gemini", "claude", "openai"]


@dataclass(slots=True, frozen=True)
class ModelCost:
    """Static pricing metadata for one provider/model combination."""

    provider: ProviderName
    model: str
    input_cost_per_1k_tokens_usd: float
    output_cost_per_1k_tokens_usd: float
    quality_tier: int = 1
    latency_tier: int = 2
    max_context_tokens: int | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)

    def estimate_cost_usd(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate request cost for the given token counts."""
        prompt = max(prompt_tokens, 0)
        completion = max(completion_tokens, 0)
        prompt_cost = (prompt / 1000.0) * self.input_cost_per_1k_tokens_usd
        completion_cost = (completion / 1000.0) * self.output_cost_per_1k_tokens_usd
        return round(prompt_cost + completion_cost, 8)


# NOTE: Values are configurable defaults used for routing/cost simulation and can
# be updated without touching routing logic. Keep this as the single pricing source.
MODEL_PRICING_TABLE: tuple[ModelCost, ...] = (
    # DeepSeek
    ModelCost(
        provider="deepseek",
        model="deepseek-chat",
        input_cost_per_1k_tokens_usd=0.00014,
        output_cost_per_1k_tokens_usd=0.00028,
        quality_tier=1,
        latency_tier=1,
        max_context_tokens=64000,
        tags=("economy", "general"),
    ),
    ModelCost(
        provider="deepseek",
        model="deepseek-reasoner",
        input_cost_per_1k_tokens_usd=0.00055,
        output_cost_per_1k_tokens_usd=0.00219,
        quality_tier=3,
        latency_tier=3,
        max_context_tokens=64000,
        tags=("reasoning",),
    ),
    # Gemini
    ModelCost(
        provider="gemini",
        model="gemini-1.5-flash",
        input_cost_per_1k_tokens_usd=0.00035,
        output_cost_per_1k_tokens_usd=0.00105,
        quality_tier=2,
        latency_tier=1,
        max_context_tokens=1000000,
        tags=("fast", "general"),
    ),
    ModelCost(
        provider="gemini",
        model="gemini-1.5-pro",
        input_cost_per_1k_tokens_usd=0.0035,
        output_cost_per_1k_tokens_usd=0.0105,
        quality_tier=4,
        latency_tier=3,
        max_context_tokens=2000000,
        tags=("high_quality", "long_context"),
    ),
    # Claude
    ModelCost(
        provider="claude",
        model="claude-3-5-haiku-latest",
        input_cost_per_1k_tokens_usd=0.0008,
        output_cost_per_1k_tokens_usd=0.004,
        quality_tier=2,
        latency_tier=1,
        max_context_tokens=200000,
        tags=("fast",),
    ),
    ModelCost(
        provider="claude",
        model="claude-3-5-sonnet-latest",
        input_cost_per_1k_tokens_usd=0.003,
        output_cost_per_1k_tokens_usd=0.015,
        quality_tier=4,
        latency_tier=2,
        max_context_tokens=200000,
        tags=("balanced",),
    ),
    # GPT-4 class
    ModelCost(
        provider="openai",
        model="gpt-4o-mini",
        input_cost_per_1k_tokens_usd=0.00015,
        output_cost_per_1k_tokens_usd=0.0006,
        quality_tier=2,
        latency_tier=1,
        max_context_tokens=128000,
        tags=("economy",),
    ),
    ModelCost(
        provider="openai",
        model="gpt-4o",
        input_cost_per_1k_tokens_usd=0.0025,
        output_cost_per_1k_tokens_usd=0.01,
        quality_tier=4,
        latency_tier=2,
        max_context_tokens=128000,
        tags=("high_quality",),
    ),
    ModelCost(
        provider="openai",
        model="gpt-4.1",
        input_cost_per_1k_tokens_usd=0.005,
        output_cost_per_1k_tokens_usd=0.015,
        quality_tier=5,
        latency_tier=3,
        max_context_tokens=128000,
        tags=("premium", "reasoning"),
    ),
)


MODEL_COST_CATALOG: dict[tuple[str, str], ModelCost] = {
    (entry.provider, entry.model): entry for entry in MODEL_PRICING_TABLE
}

PROVIDER_MODEL_IDS: dict[str, tuple[str, ...]] = {}
for entry in MODEL_PRICING_TABLE:
    existing = PROVIDER_MODEL_IDS.get(entry.provider, ())
    PROVIDER_MODEL_IDS[entry.provider] = existing + (entry.model,)


def get_model_cost(provider: str, model: str) -> ModelCost | None:
    """Fetch pricing metadata for a provider/model pair."""
    return MODEL_COST_CATALOG.get((provider.lower().strip(), model.strip()))


def list_model_costs(provider: str | None = None) -> list[ModelCost]:
    """List pricing entries optionally filtered by provider."""
    if provider is None:
        return list(MODEL_PRICING_TABLE)
    provider_key = provider.lower().strip()
    return [entry for entry in MODEL_PRICING_TABLE if entry.provider == provider_key]
