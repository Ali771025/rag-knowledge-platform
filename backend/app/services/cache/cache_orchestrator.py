"""High-level cache orchestration across semantic, RAG, and session caches."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.cache.contracts import CachedResponse, RAGCacheResult, SemanticCacheLookupResult, SessionContextPayload
from app.services.cache.rag_cache import RAGCache
from app.services.cache.semantic_cache import SemanticCache
from app.services.cache.session_cache import SessionCache


class CacheOrchestrationResult(BaseModel):
    """Structured result for cache orchestration lookup/write flows."""

    status: Literal["semantic_hit", "rag_hit", "cache_miss", "semantic_persisted"]
    requires_retrieval: bool = False
    semantic_result: SemanticCacheLookupResult | None = None
    rag_result: RAGCacheResult | None = None
    persisted_response: CachedResponse | None = None
    session_context: SessionContextPayload | None = None
    estimated_cost_saved_usd: float | None = Field(default=None, ge=0.0)
    reason: str | None = None

    model_config = ConfigDict(extra="forbid")


class CacheOrchestrator:
    """Centralized cache flow coordinator with dependency-injected services."""

    def __init__(
        self,
        semantic_cache: SemanticCache,
        rag_cache: RAGCache,
        session_cache: SessionCache,
    ) -> None:
        self.semantic_cache = semantic_cache
        self.rag_cache = rag_cache
        self.session_cache = session_cache

    async def resolve_query(
        self,
        query_text: str,
        session_id: str | None = None,
        semantic_namespace: str = "semantic",
        rag_namespace: str = "rag",
        rag_filters: dict[str, Any] | None = None,
        rag_top_k: int = 5,
        rag_retrieval_scope: str | None = None,
        semantic_embedding: list[float] | None = None,
        max_age_seconds: int | None = None,
    ) -> CacheOrchestrationResult:
        """Run ordered cache lookup: semantic first, then RAG, else retrieval required."""
        session_context = await self._safe_get_session_context(session_id=session_id)

        semantic_result = await self.semantic_cache.get_cached_response(
            query_text=query_text,
            namespace=semantic_namespace,
            embedding=semantic_embedding,
            max_age_seconds=max_age_seconds,
        )
        if semantic_result.hit:
            return CacheOrchestrationResult(
                status="semantic_hit",
                requires_retrieval=False,
                semantic_result=semantic_result,
                session_context=session_context,
                estimated_cost_saved_usd=self._estimate_cost_saved_usd(semantic_result.response),
                reason=semantic_result.reason,
            )

        rag_result = await self.rag_cache.get_cached_rag_results(
            query_text=query_text,
            namespace=rag_namespace,
            filters=rag_filters,
            top_k=rag_top_k,
            retrieval_scope=rag_retrieval_scope,
            max_age_seconds=max_age_seconds,
        )
        if rag_result.hit:
            return CacheOrchestrationResult(
                status="rag_hit",
                requires_retrieval=False,
                semantic_result=semantic_result,
                rag_result=rag_result,
                session_context=session_context,
                reason="rag_cache_hit",
            )

        return CacheOrchestrationResult(
            status="cache_miss",
            requires_retrieval=True,
            semantic_result=semantic_result,
            rag_result=rag_result,
            session_context=session_context,
            reason="downstream_retrieval_required",
        )

    async def persist_final_response(
        self,
        query_text: str,
        response_payload: dict[str, Any] | list[Any] | str | int | float | bool | None,
        namespace: str = "semantic",
        embedding: list[float] | None = None,
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
        cache_key: str | None = None,
    ) -> CacheOrchestrationResult:
        """Persist downstream final response to semantic cache."""
        persisted = await self.semantic_cache.cache_response(
            query_text=query_text,
            response_payload=response_payload,
            namespace=namespace,
            embedding=embedding,
            ttl_seconds=ttl_seconds,
            metadata=metadata,
            cache_key=cache_key,
        )
        return CacheOrchestrationResult(
            status="semantic_persisted",
            requires_retrieval=False,
            persisted_response=persisted,
            reason="semantic_cache_written",
        )

    async def lookup_semantic(self, query_text: str) -> SemanticCacheLookupResult:
        """Backward-compatible semantic-only lookup helper."""
        return await self.semantic_cache.lookup(query_text=query_text)

    async def _safe_get_session_context(self, session_id: str | None) -> SessionContextPayload | None:
        if not session_id:
            return None
        try:
            return await self.session_cache.get_session_context(session_id=session_id)
        except Exception:
            return None

    @staticmethod
    def _estimate_cost_saved_usd(response: CachedResponse | None) -> float | None:
        if response is None:
            return None
        value = response.metadata.get("estimated_cost_usd")
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
        return None
