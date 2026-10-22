"""Model routing orchestration that composes complexity, cost, and fallback planning."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.llm.contracts import ComplexityResult, LLMRequest, RoutingDecision
from app.services.llm.cost_router import CostRouter
from app.services.llm.fallback_manager import FallbackManager
from app.services.llm.query_complexity import QueryComplexityAnalyzer


class RoutingPlan(BaseModel):
    """Typed routing plan with primary decision and bounded fallback chain."""

    request_id: str = Field(..., min_length=1, max_length=128)
    complexity: ComplexityResult
    primary: RoutingDecision
    fallback_chain: list[RoutingDecision] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ModelRouter:
    """Routing orchestrator combining complexity analysis, cost routing, and fallback strategy."""

    def __init__(
        self,
        complexity_analyzer: QueryComplexityAnalyzer | None = None,
        cost_router: CostRouter | None = None,
        fallback_manager: FallbackManager | None = None,
    ) -> None:
        self.complexity_analyzer = complexity_analyzer or QueryComplexityAnalyzer()
        self.cost_router = cost_router or CostRouter()
        self.fallback_manager = fallback_manager or FallbackManager()

    async def build_routing_plan(self, request: LLMRequest) -> RoutingPlan:
        """Compute complexity, choose primary model, and attach fallback chain."""
        complexity = await self.complexity_analyzer.evaluate(request)
        primary = await self.cost_router.route(request=request, complexity=complexity)
        fallback_chain = await self.fallback_manager.build_failover_chain(primary_decision=primary)
        return RoutingPlan(
            request_id=request.request_id,
            complexity=complexity,
            primary=primary,
            fallback_chain=fallback_chain,
        )

    async def route(self, request: LLMRequest) -> RoutingDecision:
        """Return the primary routing decision with immediate fallback attached."""
        plan = await self.build_routing_plan(request)
        if not plan.fallback_chain:
            return plan.primary.model_copy(update={"reason": f"{plan.primary.reason}; fallback_chain=none"})

        first_fallback = plan.fallback_chain[0]
        chain_summary = " > ".join(f"{entry.provider}:{entry.model}" for entry in plan.fallback_chain)
        return plan.primary.model_copy(
            update={
                "fallback_provider": first_fallback.provider,
                "fallback_model": first_fallback.model,
                "reason": f"{plan.primary.reason}; fallback_chain={chain_summary}",
            }
        )
