"""Embedding client adapter."""

from __future__ import annotations

import logging
import os
from collections import OrderedDict
from threading import RLock
from time import perf_counter

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-large"


class EmbeddingClientError(Exception):
    """Base embedding client exception."""


class EmbeddingClientConfigurationError(EmbeddingClientError):
    """Raised when embedding provider config is missing."""


class EmbeddingClientAPIError(EmbeddingClientError):
    """Raised when embedding provider call fails."""


class EmbeddingClient:
    """Wrapper for text embedding providers."""

    _cache_lock = RLock()
    _vector_cache: "OrderedDict[str, list[float]]" = OrderedDict()

    def __init__(self, api_key: str | None = None, model: str = EMBEDDING_MODEL) -> None:
        self.api_key = api_key or settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self._client = None
        self._timeout_seconds = max(1.0, float(getattr(settings, "openai_embedding_timeout_sec", 6.0)))
        self._max_retries = max(0, int(getattr(settings, "openai_embedding_max_retries", 0)))
        self._cache_size = max(0, int(getattr(settings, "embedding_cache_size", 256)))

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise EmbeddingClientConfigurationError("OPENAI_API_KEY is not configured")
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                timeout=self._timeout_seconds,
                max_retries=self._max_retries,
            )
            return self._client
        except Exception as exc:
            raise EmbeddingClientAPIError("failed to initialize OpenAI client") from exc

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector for one text."""
        normalized = str(text or "").strip()
        if not normalized:
            return []

        cached = self._cache_get(normalized)
        if cached is not None:
            logger.info("embedding_cache_hit", extra={"model": self.model, "text_length": len(normalized)})
            return cached

        vectors = self.embed_batch([normalized])
        return vectors[0] if vectors else []

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts."""
        if not texts:
            return []

        started = perf_counter()
        normalized_texts = [str(text or "").strip() for text in texts]
        vectors: list[list[float]] = [[] for _ in normalized_texts]
        cache_hits = 0
        missing_indices: list[int] = []
        missing_texts: list[str] = []

        for index, text in enumerate(normalized_texts):
            if not text:
                continue
            cached = self._cache_get(text)
            if cached is not None:
                cache_hits += 1
                vectors[index] = cached
                continue
            missing_indices.append(index)
            missing_texts.append(text)

        if not missing_texts:
            logger.info(
                "embedding_batch_success",
                extra={
                    "count": len(vectors),
                    "model": self.model,
                    "cache_hits": cache_hits,
                    "cache_misses": 0,
                    "duration_ms": int((perf_counter() - started) * 1000),
                },
            )
            return vectors

        client = self._get_client()
        try:
            response = client.embeddings.create(model=self.model, input=missing_texts)
            fetched_vectors = [list(item.embedding) for item in response.data]
            for index, vector in zip(missing_indices, fetched_vectors, strict=False):
                vectors[index] = vector
                original_text = normalized_texts[index]
                if original_text:
                    self._cache_set(original_text, vector)
            logger.info(
                "embedding_batch_success",
                extra={
                    "count": len(vectors),
                    "model": self.model,
                    "cache_hits": cache_hits,
                    "cache_misses": len(missing_texts),
                    "duration_ms": int((perf_counter() - started) * 1000),
                },
            )
            return vectors
        except Exception as exc:
            raise EmbeddingClientAPIError("failed to generate embeddings") from exc

    def _cache_get(self, text: str) -> list[float] | None:
        if self._cache_size <= 0:
            return None
        key = self._cache_key(text)
        with self._cache_lock:
            vector = self._vector_cache.get(key)
            if vector is None:
                return None
            self._vector_cache.move_to_end(key)
            return list(vector)

    def _cache_set(self, text: str, vector: list[float]) -> None:
        if self._cache_size <= 0:
            return
        key = self._cache_key(text)
        with self._cache_lock:
            self._vector_cache[key] = list(vector)
            self._vector_cache.move_to_end(key)
            while len(self._vector_cache) > self._cache_size:
                self._vector_cache.popitem(last=False)

    def _cache_key(self, text: str) -> str:
        return f"{self.model}:{text}"
