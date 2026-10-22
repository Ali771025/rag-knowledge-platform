"""Deterministic cache for retrieval results produced by the RAG pipeline."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from pydantic import ValidationError

from app.models.cache.contracts import CacheInvalidateResult, CachedResponse, RAGCacheResult
from app.services.cache.redis_client import AsyncRedisClient, RedisOperationError, RedisSerializationError


class RAGPayloadCodec(Protocol):
    """Compression-ready payload transformation abstraction."""

    def encode(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Transform the payload before persistence."""

    def decode(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Transform a stored payload back to in-memory representation."""


class JsonPassthroughCodec:
    """Default payload codec that keeps JSON data unchanged."""

    def encode(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    def decode(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload


class RAGCache:
    """Deterministic cache service for retrieval result payloads."""

    def __init__(
        self,
        redis_client: AsyncRedisClient,
        payload_codec: RAGPayloadCodec | None = None,
        default_ttl_seconds: int = 900,
        min_ttl_seconds: int = 1,
        max_ttl_seconds: int = 24 * 3600,
    ) -> None:
        self.redis_client = redis_client
        self.payload_codec = payload_codec or JsonPassthroughCodec()
        self.default_ttl_seconds = default_ttl_seconds
        self.min_ttl_seconds = min_ttl_seconds
        self.max_ttl_seconds = max_ttl_seconds

    async def get_cached_rag_results(
        self,
        query_text: str,
        namespace: str = "rag",
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
        retrieval_scope: str | None = None,
        max_age_seconds: int | None = None,
    ) -> RAGCacheResult:
        """Get cached retrieval results via deterministic query fingerprint."""
        cache_key = self._derive_cache_key(
            query_text=query_text,
            filters=filters,
            top_k=top_k,
            retrieval_scope=retrieval_scope,
        )
        redis_key = self.redis_client.build_key(namespace, "retrieval", cache_key)

        try:
            payload = await self.redis_client.get_json(redis_key)
        except (RedisOperationError, RedisSerializationError):
            return RAGCacheResult(
                hit=False,
                cache_key=cache_key,
                response=None,
                source_document_ids=[],
            )

        if payload is None:
            return RAGCacheResult(
                hit=False,
                cache_key=cache_key,
                response=None,
                source_document_ids=[],
            )

        try:
            cached = CachedResponse.model_validate(payload)
        except ValidationError:
            return RAGCacheResult(
                hit=False,
                cache_key=cache_key,
                response=None,
                source_document_ids=[],
            )

        if not self._is_fresh(cached, max_age_seconds=max_age_seconds):
            return RAGCacheResult(
                hit=False,
                cache_key=cache_key,
                response=None,
                source_document_ids=[],
            )

        decoded = self._decode_payload(cached.payload)
        source_ids = self._extract_source_document_ids(decoded)
        materialized = cached.model_copy(update={"payload": decoded})
        return RAGCacheResult(
            hit=True,
            cache_key=cache_key,
            response=materialized,
            source_document_ids=source_ids,
        )

    async def cache_rag_results(
        self,
        query_text: str,
        retrieval_results: list[dict[str, Any]],
        namespace: str = "rag",
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
        retrieval_scope: str | None = None,
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CachedResponse:
        """Cache top-k retrieval results keyed by normalized query fingerprint."""
        ttl = self._resolve_ttl(ttl_seconds)
        cache_key = self._derive_cache_key(
            query_text=query_text,
            filters=filters,
            top_k=top_k,
            retrieval_scope=retrieval_scope,
        )
        redis_key = self.redis_client.build_key(namespace, "retrieval", cache_key)
        now = datetime.now(timezone.utc)

        encoded_payload = self.payload_codec.encode(
            {
                "results": retrieval_results[: max(top_k, 0)],
                "top_k": top_k,
                "filters": filters or {},
                "retrieval_scope": retrieval_scope,
            }
        )
        source_ids = self._extract_source_document_ids(encoded_payload)

        record = CachedResponse(
            cache_key=cache_key,
            namespace=namespace,
            payload=encoded_payload,
            ttl_seconds=ttl,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
            metadata={
                **(metadata or {}),
                "source_document_ids": source_ids,
                "query_fingerprint": cache_key,
            },
        )
        await self.redis_client.set_json(redis_key, record.model_dump(mode="json"), ttl_seconds=ttl)
        return record

    async def invalidate_rag_cache(
        self,
        namespace: str = "rag",
        cache_key: str | None = None,
        query_text: str | None = None,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
        retrieval_scope: str | None = None,
    ) -> CacheInvalidateResult:
        """Invalidate one deterministic retrieval cache entry."""
        if cache_key is None:
            if query_text is None:
                raise ValueError("Either cache_key or query_text must be provided for cache invalidation.")
            cache_key = self._derive_cache_key(
                query_text=query_text,
                filters=filters,
                top_k=top_k,
                retrieval_scope=retrieval_scope,
            )

        redis_key = self.redis_client.build_key(namespace, "retrieval", cache_key)
        deleted = await self.redis_client.delete(redis_key)
        return CacheInvalidateResult(
            success=deleted > 0,
            namespace=namespace,
            cache_key=cache_key,
            invalidated_count=deleted,
            message="rag_cache_invalidated",
        )

    async def lookup(self, query_text: str, namespace: str = "rag") -> RAGCacheResult:
        """Backward-compatible alias for retrieval cache lookup."""
        return await self.get_cached_rag_results(query_text=query_text, namespace=namespace)

    async def store(self, cache_entry: CachedResponse) -> bool:
        """Backward-compatible alias for retrieval cache store operation."""
        payload = cache_entry.payload
        if not isinstance(payload, dict):
            raise ValueError("RAG cache store expects payload to be a dict with retrieval result structure.")

        results = payload.get("results", [])
        if not isinstance(results, list):
            raise ValueError("RAG cache payload field 'results' must be a list.")

        await self.cache_rag_results(
            query_text=cache_entry.cache_key,
            retrieval_results=results,
            namespace=cache_entry.namespace,
            filters=payload.get("filters", {}),
            top_k=int(payload.get("top_k", len(results) or 5)),
            retrieval_scope=payload.get("retrieval_scope"),
            ttl_seconds=cache_entry.ttl_seconds,
            metadata=cache_entry.metadata,
        )
        return True

    def _resolve_ttl(self, requested_ttl: int | None) -> int:
        ttl = self.default_ttl_seconds if requested_ttl is None else requested_ttl
        if ttl < self.min_ttl_seconds or ttl > self.max_ttl_seconds:
            raise ValueError(
                f"ttl_seconds must be between {self.min_ttl_seconds} and {self.max_ttl_seconds}, got {ttl}."
            )
        return ttl

    @staticmethod
    def _derive_cache_key(
        query_text: str,
        filters: dict[str, Any] | None,
        top_k: int,
        retrieval_scope: str | None,
    ) -> str:
        normalized_query = " ".join(query_text.strip().lower().split())
        normalized_payload = {
            "query": normalized_query,
            "filters": filters or {},
            "top_k": top_k,
            "retrieval_scope": retrieval_scope,
        }
        digest = hashlib.sha256(json.dumps(normalized_payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        return digest.hexdigest()

    @staticmethod
    def _is_fresh(cached: CachedResponse, max_age_seconds: int | None) -> bool:
        now = datetime.now(timezone.utc)
        if cached.expires_at and cached.expires_at <= now:
            return False
        if max_age_seconds is None:
            return True
        return cached.created_at + timedelta(seconds=max_age_seconds) > now

    def _decode_payload(self, payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        return self.payload_codec.decode(payload)

    @staticmethod
    def _extract_source_document_ids(payload: Any) -> list[str]:
        if not isinstance(payload, dict):
            return []
        results = payload.get("results")
        if not isinstance(results, list):
            return []

        source_ids: list[str] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            value = item.get("document_id") or item.get("source_document_id") or item.get("id")
            if isinstance(value, str) and value:
                source_ids.append(value)
        return source_ids
