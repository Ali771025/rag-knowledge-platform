"""Vector retrieval service backed by Qdrant repository.

This component orchestrates vector retrieval only:
- accepts embedding-ready queries, or
- consumes an embedding provider abstraction for text-to-vector conversion.

It must not implement ingestion embedding pipelines, write operations, or index setup.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.embedding_client import EmbeddingClient
from app.rag.models.rag_types import TraceId
from app.rag.repositories.qdrant_repository import QdrantRepository
from app.rag.schemas.retrieval import RetrievedChunk


class EmbeddingProvider(Protocol):
    """Abstraction for runtime embedding inference."""

    def embed_text(self, text: str) -> list[float]:
        """Return embedding vector for input text."""


class VectorRetrieverError(Exception):
    """Raised when vector retrieval preconditions or execution fail."""


class VectorQueryInput(BaseModel):
    """Input contract for vector retrieval execution."""

    trace_id: TraceId
    query_text: str | None = None
    query_vector: list[float] | None = None
    top_k: int = Field(default=20, ge=1, le=100)
    filters: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def _validate_query_payload(self) -> "VectorQueryInput":
        has_text = bool(self.query_text)
        has_vector = bool(self.query_vector)
        if not has_text and not has_vector:
            raise ValueError("either query_vector or query_text must be provided")
        return self


class VectorRetriever:
    """Service for read-only vector retrieval with score normalization."""

    def __init__(
        self,
        repository: QdrantRepository | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.repository = repository or QdrantRepository()
        self.embedding_provider = embedding_provider

    def retrieve(self, query_input: VectorQueryInput) -> list[RetrievedChunk]:
        """Execute vector retrieval and return normalized `RetrievedChunk` items."""
        query_vector = self._resolve_query_vector(query_input)

        chunks = self.repository.search(
            trace_id=query_input.trace_id,
            query_vector=query_vector,
            top_k=query_input.top_k,
            filters=query_input.filters,
        )
        if not chunks:
            return []

        normalized_scores = self._normalize_scores(chunks)
        output: list[RetrievedChunk] = []
        for chunk, normalized in zip(chunks, normalized_scores, strict=True):
            metadata = dict(chunk.metadata or {})
            metadata["raw_score"] = chunk.score
            metadata["normalized_score"] = normalized
            output.append(
                chunk.model_copy(
                    update={
                        "score": normalized,
                        "metadata": metadata,
                    },
                    deep=True,
                )
            )
        return output

    def _resolve_query_vector(self, query_input: VectorQueryInput) -> list[float]:
        if query_input.query_vector:
            return query_input.query_vector

        query_text = query_input.query_text
        if not query_text:
            raise VectorRetrieverError("query_text is required when query_vector is not provided")

        provider = self.embedding_provider
        if provider is None:
            # Use existing embedding adapter by interface instead of ingestion embedding pipeline.
            provider = EmbeddingClient()

        try:
            vector = provider.embed_text(query_text)
        except Exception as exc:
            raise VectorRetrieverError("failed to generate query embedding") from exc

        if not vector:
            raise VectorRetrieverError("embedding provider returned an empty query vector")

        return vector

    def _normalize_scores(self, chunks: list[RetrievedChunk]) -> list[float]:
        raw_scores = [chunk.score for chunk in chunks if chunk.score is not None]
        if not raw_scores:
            return self._rank_fallback_scores(len(chunks))

        min_score = min(raw_scores)
        max_score = max(raw_scores)
        if max_score == min_score:
            return self._rank_fallback_scores(len(chunks))

        normalized: list[float] = []
        for chunk in chunks:
            if chunk.score is None:
                normalized.append(0.0)
                continue
            score = (chunk.score - min_score) / (max_score - min_score)
            normalized.append(round(max(0.0, min(1.0, score)), 6))
        return normalized

    def _rank_fallback_scores(self, total: int) -> list[float]:
        if total <= 0:
            return []
        if total == 1:
            return [1.0]

        scores: list[float] = []
        denominator = total - 1
        for index in range(total):
            rank_score = 1.0 - (index / denominator)
            scores.append(round(rank_score, 6))
        return scores
