"""Lazy runtime service registry for cache/routing/cost/observability components."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.cache.cache_orchestrator import CacheOrchestrator
from app.services.cache.rag_cache import RAGCache
from app.services.cache.redis_client import AsyncRedisClient
from app.services.cache.semantic_cache import SemanticCache
from app.services.cache.session_cache import SessionCache
from app.services.cost.budget_guard import BudgetGuard
from app.services.cost.cost_tracker import CostTracker
from app.services.llm.cost_router import CostRouter
from app.services.llm.fallback_manager import FallbackManager
from app.services.llm.model_router import ModelRouter
from app.services.llm.query_complexity import QueryComplexityAnalyzer
from app.services.llm.unified_client import UnifiedLLMClient
from app.services.observability.cache_metrics import CacheMetricsRecorder
from app.services.observability.llm_metrics import LLMMetricsRecorder
from app.services.token_usage_tracker import TokenUsageTracker


@dataclass(slots=True)
class RuntimeServices:
    """Shared runtime services used by pipeline and admin visibility endpoints."""

    redis_client: AsyncRedisClient
    cache_metrics: CacheMetricsRecorder
    llm_metrics: LLMMetricsRecorder
    semantic_cache: SemanticCache
    rag_cache: RAGCache
    session_cache: SessionCache
    cache_orchestrator: CacheOrchestrator
    complexity_analyzer: QueryComplexityAnalyzer
    cost_router: CostRouter
    fallback_manager: FallbackManager
    model_router: ModelRouter
    llm_client: UnifiedLLMClient
    cost_tracker: CostTracker
    budget_guard: BudgetGuard
    token_usage_tracker: TokenUsageTracker


_runtime_services: RuntimeServices | None = None


def get_runtime_services() -> RuntimeServices:
    """Return lazily-initialized runtime service singletons."""
    global _runtime_services
    if _runtime_services is None:
        redis_client = AsyncRedisClient()
        cache_metrics = CacheMetricsRecorder()
        llm_metrics = LLMMetricsRecorder()
        semantic_cache = SemanticCache(redis_client=redis_client, metrics_recorder=cache_metrics)
        rag_cache = RAGCache(redis_client=redis_client)
        session_cache = SessionCache(redis_client=redis_client)
        cache_orchestrator = CacheOrchestrator(
            semantic_cache=semantic_cache,
            rag_cache=rag_cache,
            session_cache=session_cache,
        )
        complexity_analyzer = QueryComplexityAnalyzer()
        cost_router = CostRouter()
        fallback_manager = FallbackManager()
        model_router = ModelRouter(
            complexity_analyzer=complexity_analyzer,
            cost_router=cost_router,
            fallback_manager=fallback_manager,
        )
        llm_client = UnifiedLLMClient()
        cost_tracker = CostTracker()
        budget_guard = BudgetGuard()
        token_usage_tracker = TokenUsageTracker()

        _runtime_services = RuntimeServices(
            redis_client=redis_client,
            cache_metrics=cache_metrics,
            llm_metrics=llm_metrics,
            semantic_cache=semantic_cache,
            rag_cache=rag_cache,
            session_cache=session_cache,
            cache_orchestrator=cache_orchestrator,
            complexity_analyzer=complexity_analyzer,
            cost_router=cost_router,
            fallback_manager=fallback_manager,
            model_router=model_router,
            llm_client=llm_client,
            cost_tracker=cost_tracker,
            budget_guard=budget_guard,
            token_usage_tracker=token_usage_tracker,
        )
    return _runtime_services
