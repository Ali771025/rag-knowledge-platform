from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.token_monitoring import TokenProvider
from app.services.llm.model_costs import get_model_cost

_COST_QUANT = Decimal("0.000000001")


class APIKeyHashingResult(BaseModel):
    key_hash: str = Field(..., min_length=64, max_length=64)
    key_fingerprint: str = Field(..., min_length=6, max_length=24)
    key_alias: str = Field(..., min_length=4, max_length=32)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, protected_namespaces=())


class APIKeyHasher:
    @staticmethod
    def hash_key(raw_key: str) -> APIKeyHashingResult:
        normalized = raw_key.strip()
        if not normalized:
            raise ValueError("API key must not be empty")

        digest = sha256(normalized.encode("utf-8")).hexdigest()
        fingerprint = digest[:12]
        alias = f"••••{normalized[-4:]}" if len(normalized) >= 4 else "••••"

        return APIKeyHashingResult(
            key_hash=digest,
            key_fingerprint=fingerprint,
            key_alias=alias,
        )


class PricingCalculationResult(BaseModel):
    provider: str
    model_name: str
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cost_usd: Decimal = Field(ge=Decimal("0"))
    pricing_found: bool = True

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, protected_namespaces=())


class TokenPricingEngine:
    def __init__(self) -> None:
        self._aliases: dict[str, str] = {
            "anthropic": "claude",
        }

    def _resolve_provider_key(self, provider: str | TokenProvider) -> str:
        raw = provider.value if isinstance(provider, TokenProvider) else str(provider)
        key = raw.strip().lower()
        return self._aliases.get(key, key)

    def get_model_pricing(self, provider: str | TokenProvider, model_name: str) -> ModelCost | None:
        provider_key = self._resolve_provider_key(provider)
        return get_model_cost(provider=provider_key, model=model_name.strip())

    def calculate_cost(
        self,
        *,
        provider: str | TokenProvider,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> PricingCalculationResult:
        prompt = max(int(prompt_tokens), 0)
        completion = max(int(completion_tokens), 0)
        total = prompt + completion

        pricing = self.get_model_pricing(provider=provider, model_name=model_name)
        provider_value = provider.value if isinstance(provider, TokenProvider) else str(provider).strip().lower()

        if pricing is None:
            return PricingCalculationResult(
                provider=provider_value,
                model_name=model_name,
                prompt_tokens=prompt,
                completion_tokens=completion,
                total_tokens=total,
                cost_usd=Decimal("0").quantize(_COST_QUANT),
                pricing_found=False,
            )

        prompt_cost = Decimal(prompt) / Decimal(1000) * Decimal(str(pricing.input_cost_per_1k_tokens_usd))
        completion_cost = Decimal(completion) / Decimal(1000) * Decimal(str(pricing.output_cost_per_1k_tokens_usd))
        total_cost = (prompt_cost + completion_cost).quantize(_COST_QUANT, rounding=ROUND_HALF_UP)

        return PricingCalculationResult(
            provider=provider_value,
            model_name=model_name,
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
            cost_usd=total_cost,
            pricing_found=True,
        )


class TokenUsageEvent(BaseModel):
    api_key_id: str
    provider: TokenProvider
    model_name: str
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    request_id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, protected_namespaces=())
