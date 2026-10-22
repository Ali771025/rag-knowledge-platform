"""Bounded provider/model failover manager with circuit-breaker abstraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.models.llm.contracts import LLMRequest, LLMResponse, RoutingDecision
from app.services.llm.model_costs import PROVIDER_MODEL_IDS
from app.services.llm.unified_client import LLMTimeoutError, ProviderExecutionError, RetryableLLMError

FailureKind = Literal["transient", "permanent", "unknown"]


class CircuitBreaker(Protocol):
    """Circuit-breaker abstraction for provider/model health state."""

    async def is_open(self, provider: str, model: str) -> bool:
        """Return whether the circuit is currently open for this route."""

    async def record_failure(self, provider: str, model: str) -> None:
        """Record a failed attempt for this route."""

    async def record_success(self, provider: str, model: str) -> None:
        """Record a successful attempt and reset failure state."""


@dataclass(slots=True)
class InMemoryCircuitBreaker:
    """Simple in-memory circuit breaker suited for service-level integration tests."""

    failure_threshold: int = 3
    open_duration_seconds: int = 30
    _failures: dict[tuple[str, str], int] = field(default_factory=dict)
    _opened_until: dict[tuple[str, str], datetime] = field(default_factory=dict)

    async def is_open(self, provider: str, model: str) -> bool:
        key = (provider, model)
        until = self._opened_until.get(key)
        if until is None:
            return False
        if until <= datetime.now(timezone.utc):
            self._opened_until.pop(key, None)
            self._failures.pop(key, None)
            return False
        return True

    async def record_failure(self, provider: str, model: str) -> None:
        key = (provider, model)
        count = self._failures.get(key, 0) + 1
        self._failures[key] = count
        if count >= self.failure_threshold:
            self._opened_until[key] = datetime.now(timezone.utc) + timedelta(seconds=self.open_duration_seconds)

    async def record_success(self, provider: str, model: str) -> None:
        key = (provider, model)
        self._failures.pop(key, None)
        self._opened_until.pop(key, None)


class FailoverOutcome(BaseModel):
    """Structured failover evaluation outcome."""

    success: bool
    classification: FailureKind
    attempted_routes: list[RoutingDecision] = Field(default_factory=list)
    selected_route: RoutingDecision | None = None
    exhausted: bool = False
    reason: str = Field(..., min_length=1, max_length=512)

    model_config = ConfigDict(extra="forbid")


@dataclass(slots=True)
class FallbackManagerConfig:
    """Configuration for fallback sequence and classification behavior."""

    max_failover_hops: int = 3
    fallback_provider_chain: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "deepseek": ("gemini", "claude", "openai"),
            "gemini": ("claude", "openai"),
            "claude": ("openai",),
            "openai": (),
        }
    )
    default_provider_model: dict[str, str] = field(
        default_factory=lambda: {
            "deepseek": "deepseek-chat",
            "gemini": "gemini-1.5-flash",
            "claude": "claude-3-5-sonnet-latest",
            "openai": "gpt-4o",
        }
    )


class FallbackManager:
    """Explicit and bounded failover sequencing with loop prevention."""

    def __init__(
        self,
        circuit_breaker: CircuitBreaker | None = None,
        config: FallbackManagerConfig | None = None,
    ) -> None:
        self.config = config or FallbackManagerConfig()
        self.circuit_breaker = circuit_breaker or InMemoryCircuitBreaker()

    async def evaluate_failover(
        self,
        request: LLMRequest,
        primary_decision: RoutingDecision,
        failure: Exception | None = None,
        failed_response: LLMResponse | None = None,
        attempted_routes: list[RoutingDecision] | None = None,
    ) -> FailoverOutcome:
        """Classify failure and return next bounded fallback route when available."""
        _ = request
        classification = self.classify_failure(failure=failure, failed_response=failed_response)
        attempted = list(attempted_routes or [])
        attempted.append(primary_decision)

        await self.circuit_breaker.record_failure(primary_decision.provider, primary_decision.model)

        if classification == "permanent":
            return FailoverOutcome(
                success=False,
                classification=classification,
                attempted_routes=attempted,
                selected_route=None,
                exhausted=True,
                reason="permanent_failure_no_retry",
            )

        chain = await self.build_failover_chain(primary_decision=primary_decision, attempted_routes=attempted)
        if not chain:
            return FailoverOutcome(
                success=False,
                classification=classification,
                attempted_routes=attempted,
                selected_route=None,
                exhausted=True,
                reason="fallback_exhausted_or_circuit_open",
            )

        return FailoverOutcome(
            success=True,
            classification=classification,
            attempted_routes=attempted,
            selected_route=chain[0],
            exhausted=False,
            reason="fallback_selected",
        )

    async def resolve(
        self,
        request: LLMRequest,
        primary_decision: RoutingDecision,
        failed_response: LLMResponse | None = None,
    ) -> RoutingDecision:
        """Backward-compatible single-step fallback resolution."""
        outcome = await self.evaluate_failover(
            request=request,
            primary_decision=primary_decision,
            failure=None,
            failed_response=failed_response,
            attempted_routes=[],
        )
        if outcome.selected_route is not None:
            return outcome.selected_route

        return primary_decision.model_copy(
            update={
                "reason": f"{primary_decision.reason}; fallback_exhausted classification={outcome.classification}",
            }
        )

    def classify_failure(
        self,
        failure: Exception | None = None,
        failed_response: LLMResponse | None = None,
    ) -> FailureKind:
        """Classify failure into transient/permanent to guide retry vs failover."""
        if isinstance(failure, (RetryableLLMError, LLMTimeoutError)):
            return "transient"
        if isinstance(failure, ProviderExecutionError):
            return "permanent"

        if failed_response is None:
            return "unknown"

        marker = (failed_response.finish_reason or "").lower()
        if any(item in marker for item in ("timeout", "rate_limit", "overload", "unavailable", "busy")):
            return "transient"
        if any(item in marker for item in ("invalid_request", "forbidden", "unauthorized", "policy")):
            return "permanent"
        return "unknown"

    async def build_failover_chain(
        self,
        primary_decision: RoutingDecision,
        attempted_routes: list[RoutingDecision] | None = None,
    ) -> list[RoutingDecision]:
        """Build a bounded fallback chain while avoiding loops and open circuits."""
        attempted_routes = attempted_routes or []
        visited = {(entry.provider, entry.model) for entry in attempted_routes}
        visited.add((primary_decision.provider, primary_decision.model))

        provider_order = self.config.fallback_provider_chain.get(primary_decision.provider, ())
        chain: list[RoutingDecision] = []
        for provider in provider_order:
            if len(chain) >= self.config.max_failover_hops:
                break
            model = self._select_provider_model(provider=provider)
            key = (provider, model)
            if key in visited:
                continue
            if await self.circuit_breaker.is_open(provider, model):
                continue

            chain.append(
                RoutingDecision(
                    provider=provider,
                    model=model,
                    reason=f"fallback_from={primary_decision.provider}; strategy=ordered_failover",
                    complexity=primary_decision.complexity,
                )
            )
            visited.add(key)

        return chain

    def _select_provider_model(self, provider: str) -> str:
        preferred = self.config.default_provider_model.get(provider)
        if preferred:
            return preferred
        known = PROVIDER_MODEL_IDS.get(provider, ())
        if known:
            return known[0]
        raise ValueError(f"No model mapping found for provider '{provider}'.")
