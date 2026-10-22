"""Semantic response cache service with vector-search lookup."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any, Protocol

from pydantic import ValidationError

from app.models.cache.contracts import CacheInvalidateResult, CachedResponse, SemanticCacheLookupResult
from app.services.cache.redis_client import AsyncRedisClient, RedisOperationError, RedisSerializationError

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class SemanticVectorMatch:
    """Minimal vector-search match returned by a semantic index."""

    cache_key: str
    score: float
    metadata: dict[str, Any] | None = None


class SemanticVectorStore(Protocol):
    """Abstraction for semantic vector index search/upsert/delete."""

    async def search(self, namespace: str, embedding: list[float], top_k: int) -> list[SemanticVectorMatch]:
        """Return top semantic matches for an embedding vector."""

    async def upsert(
        self,
        namespace: str,
        cache_key: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Upsert embedding data for semantic lookup."""

    async def delete(self, namespace: str, cache_key: str) -> None:
        """Delete a semantic index record for the given cache key."""


class EmbeddingProvider(Protocol):
    """Abstraction for generating embeddings used in semantic matching."""

    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector from free text."""


class SemanticCache:
    """Semantic cache service with configurable threshold and TTL controls."""

    def __init__(
        self,
        redis_client: AsyncRedisClient,
        vector_store: SemanticVectorStore | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        metrics_recorder: Any | None = None,
        default_ttl_seconds: int = 3600,
        min_ttl_seconds: int = 1,
        max_ttl_seconds: int = 7 * 24 * 3600,
        similarity_threshold: float = 0.85,
        lookup_top_k: int = 5,
    ) -> None:
        self.redis_client = redis_client
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.metrics_recorder = metrics_recorder
        self.default_ttl_seconds = default_ttl_seconds
        self.min_ttl_seconds = min_ttl_seconds
        self.max_ttl_seconds = max_ttl_seconds
        self.similarity_threshold = self._validate_threshold(similarity_threshold)
        self.lookup_top_k = lookup_top_k

    async def get_cached_response(
        self,
        query_text: str,
        namespace: str = "semantic",
        embedding: list[float] | None = None,
        similarity_threshold: float | None = None,
        max_age_seconds: int | None = None,
        top_k: int | None = None,
    ) -> SemanticCacheLookupResult:
        """Resolve the best semantic cache hit and materialize payload from Redis."""
        started = perf_counter()
        threshold = self.similarity_threshold if similarity_threshold is None else self._validate_threshold(
            similarity_threshold
        )

        miss_result = SemanticCacheLookupResult(
            hit=False,
            cache_key=self._fallback_cache_key(query_text=query_text, namespace=namespace),
            similarity_score=None,
            response=None,
            reason="cache_miss",
        )

        if self.vector_store is None:
            miss_result.reason = "vector_store_unavailable"
            self._record_metrics(result=miss_result, namespace=namespace, latency_ms=self._elapsed_ms(started))
            return miss_result

        resolved_embedding = await self._resolve_embedding(query_text=query_text, embedding=embedding)
        if not resolved_embedding:
            miss_result.reason = "embedding_unavailable"
            self._record_metrics(result=miss_result, namespace=namespace, latency_ms=self._elapsed_ms(started))
            return miss_result

        try:
            matches = await self.vector_store.search(
                namespace=namespace,
                embedding=resolved_embedding,
                top_k=top_k or self.lookup_top_k,
            )
        except Exception as exc:  # pragma: no cover - defensive integration guard
            logger.warning("Semantic vector search failed for namespace=%s: %s", namespace, exc)
            miss_result.reason = "vector_search_failed"
            self._record_metrics(result=miss_result, namespace=namespace, latency_ms=self._elapsed_ms(started))
            return miss_result

        for match in matches:
            self._safe_metric_call("semantic_cache_similarity_score", namespace=namespace, score=match.score)
            if match.score < threshold:
                continue

            redis_key = self.redis_client.build_key(namespace, match.cache_key)
            payload = await self._safe_get_payload(redis_key=redis_key)
            if payload is None:
                continue

            try:
                cached = CachedResponse.model_validate(payload)
            except ValidationError:
                logger.debug("Semantic cache payload validation failed for key=%s", redis_key)
                continue

            if not self._is_fresh(cached, max_age_seconds=max_age_seconds):
                continue

            hit_result = SemanticCacheLookupResult(
                hit=True,
                cache_key=match.cache_key,
                similarity_score=match.score,
                response=cached,
                reason="hit",
            )
            self._record_metrics(result=hit_result, namespace=namespace, latency_ms=self._elapsed_ms(started))
            return hit_result

        miss_result.reason = "no_valid_match"
        self._record_metrics(result=miss_result, namespace=namespace, latency_ms=self._elapsed_ms(started))
        return miss_result

    async def cache_response(
        self,
        query_text: str,
        response_payload: dict[str, Any] | list[Any] | str | int | float | bool | None,
        namespace: str = "semantic",
        embedding: list[float] | None = None,
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
        cache_key: str | None = None,
    ) -> CachedResponse:
        """Persist semantic response payload in Redis and semantic index."""
        ttl = self._resolve_ttl(ttl_seconds)
        now = datetime.now(timezone.utc)
        resolved_cache_key = cache_key or self._generate_cache_key(query_text=query_text, namespace=namespace)
        record = CachedResponse(
            cache_key=resolved_cache_key,
            namespace=namespace,
            payload=response_payload,
            ttl_seconds=ttl,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
            metadata=dict(metadata or {}),
        )

        redis_key = self.redis_client.build_key(namespace, resolved_cache_key)
        await self.redis_client.set_json(key=redis_key, value=record.model_dump(mode="json"), ttl_seconds=ttl)

        resolved_embedding = await self._resolve_embedding(query_text=query_text, embedding=embedding)
        if self.vector_store is not None and resolved_embedding:
            try:
                await self.vector_store.upsert(
                    namespace=namespace,
                    cache_key=resolved_cache_key,
                    embedding=resolved_embedding,
                    metadata={"redis_key": redis_key},
                )
            except Exception as exc:  # pragma: no cover - defensive integration guard
                logger.warning("Semantic vector upsert failed for namespace=%s key=%s: %s", namespace, resolved_cache_key, exc)

        return record

    async def invalidate_cache(
        self,
        cache_key: str,
        namespace: str = "semantic",
    ) -> CacheInvalidateResult:
        """Invalidate a cached response in Redis and semantic index."""
        redis_key = self.redis_client.build_key(namespace, cache_key)
        invalidated_count = await self.redis_client.delete(redis_key)
        vector_error = False

        if self.vector_store is not None:
            try:
                await self.vector_store.delete(namespace=namespace, cache_key=cache_key)
            except Exception as exc:  # pragma: no cover - defensive integration guard
                vector_error = True
                logger.warning("Semantic vector delete failed for namespace=%s key=%s: %s", namespace, cache_key, exc)

        message = "cache_entry_invalidated"
        if vector_error:
            message = "redis_invalidated_vector_delete_failed"

        return CacheInvalidateResult(
            success=invalidated_count > 0,
            namespace=namespace,
            cache_key=cache_key,
            invalidated_count=invalidated_count,
            message=message,
        )

    async def lookup(self, query_text: str, namespace: str = "semantic") -> SemanticCacheLookupResult:
        """Backward-compatible alias for semantic cache lookup."""
        return await self.get_cached_response(query_text=query_text, namespace=namespace)

    async def store(self, cache_entry: CachedResponse) -> bool:
        """Backward-compatible alias for semantic cache store operation."""
        await self.cache_response(
            query_text=cache_entry.cache_key,
            response_payload=cache_entry.payload,
            namespace=cache_entry.namespace,
            ttl_seconds=cache_entry.ttl_seconds,
            metadata=cache_entry.metadata,
            cache_key=cache_entry.cache_key,
        )
        return True

    async def _resolve_embedding(self, query_text: str, embedding: list[float] | None) -> list[float] | None:
        if embedding is not None:
            return embedding
        if self.embedding_provider is None:
            return None
        try:
            return await self.embedding_provider.embed_text(query_text)
        except Exception as exc:  # pragma: no cover - defensive integration guard
            logger.warning("Embedding generation failed: %s", exc)
            return None

    async def _safe_get_payload(self, redis_key: str) -> dict[str, Any] | list[Any] | str | int | float | bool | None:
        try:
            return await self.redis_client.get_json(redis_key)
        except (RedisOperationError, RedisSerializationError) as exc:
            logger.debug("Semantic cache payload read failed for key=%s: %s", redis_key, exc)
            return None

    def _resolve_ttl(self, requested_ttl: int | None) -> int:
        ttl = self.default_ttl_seconds if requested_ttl is None else requested_ttl
        if ttl < self.min_ttl_seconds or ttl > self.max_ttl_seconds:
            raise ValueError(
                f"ttl_seconds must be between {self.min_ttl_seconds} and {self.max_ttl_seconds}, got {ttl}."
            )
        return ttl

    @staticmethod
    def _validate_threshold(threshold: float) -> float:
        if threshold < 0 or threshold > 1:
            raise ValueError(f"similarity_threshold must be within [0, 1], got {threshold}.")
        return threshold

    @staticmethod
    def _generate_cache_key(query_text: str, namespace: str) -> str:
        normalized = " ".join(query_text.strip().lower().split())
        fingerprint = hashlib.sha256(f"{namespace}:{normalized}".encode("utf-8")).hexdigest()
        return fingerprint

    def _fallback_cache_key(self, query_text: str, namespace: str) -> str:
        return self._generate_cache_key(query_text=query_text, namespace=namespace)

    @staticmethod
    def _is_fresh(cached: CachedResponse, max_age_seconds: int | None) -> bool:
        now = datetime.now(timezone.utc)
        if cached.expires_at and cached.expires_at <= now:
            return False
        if max_age_seconds is None:
            return True
        if cached.created_at + timedelta(seconds=max_age_seconds) <= now:
            return False
        return True

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return int((perf_counter() - started) * 1000)

    def _record_metrics(self, result: SemanticCacheLookupResult, namespace: str, latency_ms: int) -> None:
        self._safe_metric_call("semantic_cache_lookup_latency_ms", namespace=namespace, latency_ms=latency_ms)
        if result.similarity_score is not None:
            self._safe_metric_call("semantic_cache_similarity_score", namespace=namespace, score=result.similarity_score)

        if result.hit:
            self._safe_metric_call("semantic_cache_hit", namespace=namespace, latency_ms=latency_ms)
            estimated_saved = self._extract_estimated_cost_saved(result)
            if estimated_saved is not None:
                self._safe_metric_call(
                    "semantic_cache_estimated_cost_saved",
                    namespace=namespace,
                    estimated_cost_saved=estimated_saved,
                )
        else:
            self._safe_metric_call("semantic_cache_miss", namespace=namespace, latency_ms=latency_ms, reason=result.reason)

    @staticmethod
    def _extract_estimated_cost_saved(result: SemanticCacheLookupResult) -> float | None:
        if result.response is None:
            return None
        value = result.response.metadata.get("estimated_cost_usd")
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
        return None

    def _safe_metric_call(self, method_name: str, **kwargs: Any) -> None:
        if self.metrics_recorder is None:
            return
        method = getattr(self.metrics_recorder, method_name, None)
        if not callable(method):
            return
        try:
            method(**kwargs)
        except Exception as exc:  # pragma: no cover - fault isolation for metrics/log hooks
            logger.debug("Semantic cache metrics hook failed: method=%s error=%s", method_name, exc)
