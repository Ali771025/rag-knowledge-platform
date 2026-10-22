"""Read-only Qdrant repository for vector retrieval.

This adapter only executes search reads against an existing collection.
It must not create collections, upsert vectors, or perform migrations.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.qdrant_client import QdrantClientAdapter, QdrantConnectionError
from app.core.vector_payload import QDRANT_CHUNK_TEXT_KEY, QDRANT_CHUNK_TEXT_LEGACY_KEY
from app.rag.models.rag_types import RetrievalSource, TraceId
from app.rag.schemas.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)


class QdrantRepositoryError(Exception):
    """Raised when Qdrant read operations fail."""


class QdrantRepository:
    """Read-only adapter for vector search in Qdrant."""

    def __init__(self, qdrant_client: QdrantClientAdapter | None = None) -> None:
        self.qdrant_client = qdrant_client or QdrantClientAdapter()

    def search(
        self,
        *,
        trace_id: TraceId,
        query_vector: list[float],
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Search Qdrant and map points into `RetrievedChunk` records."""
        if not query_vector:
            return []

        safe_top_k = max(1, min(top_k, 100))

        try:
            client = self.qdrant_client._get_client()  # noqa: SLF001 - read-only repository access.
            query_filter = self._build_query_filter(filters)
            results = client.search(
                collection_name=self.qdrant_client.collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=safe_top_k,
                with_payload=True,
                with_vectors=False,
            )
        except QdrantConnectionError as exc:
            raise QdrantRepositoryError("Qdrant is unavailable for search reads") from exc
        except Exception as exc:
            raise QdrantRepositoryError("failed to search Qdrant") from exc

        chunks: list[RetrievedChunk] = []
        for index, point in enumerate(results, start=1):
            payload = self._normalize_payload(getattr(point, "payload", None))

            chunk_id = self._to_text(payload.get("chunk_id")) or self._to_text(getattr(point, "id", None))
            content = self._to_text(payload.get(QDRANT_CHUNK_TEXT_KEY)) or self._to_text(payload.get(QDRANT_CHUNK_TEXT_LEGACY_KEY))
            if not chunk_id or not content:
                logger.debug("skip_qdrant_point_missing_required_fields", extra={"trace_id": trace_id})
                continue

            document_id = self._to_text(payload.get("document_id")) or chunk_id
            source_id = self._to_text(payload.get("source_id")) or f"qdrant:{chunk_id}"
            score = self._safe_float(getattr(point, "score", None))

            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    trace_id=trace_id,
                    retrieval_source=RetrievalSource.VECTOR,
                    source_id=source_id,
                    document_id=document_id,
                    content=content,
                    score=score,
                    rank=index,
                    source_uri=self._to_text(payload.get("source_uri")),
                    source_title=self._to_text(payload.get("source_title")) or self._to_text(payload.get("title")),
                    start_char=self._safe_int(payload.get("start_char")),
                    end_char=self._safe_int(payload.get("end_char")),
                    metadata=self._build_metadata(payload, point_id=chunk_id),
                )
            )

        return chunks

    def _build_query_filter(self, filters: dict[str, Any] | None) -> Any:
        if not filters:
            return None
        qdrant_filter_payload: dict[str, Any] | None = None
        if isinstance(filters.get("qdrant"), dict):
            qdrant_filter_payload = filters.get("qdrant")
        elif isinstance(filters, dict):
            qdrant_filter_payload = filters
        try:
            from qdrant_client.models import Filter
            if not qdrant_filter_payload:
                return None
            return Filter(**qdrant_filter_payload)
        except Exception as exc:
            raise QdrantRepositoryError("invalid qdrant filter payload") from exc

    def _normalize_payload(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            return payload
        return {}

    def _build_metadata(self, payload: dict[str, Any], *, point_id: str) -> dict[str, Any] | None:
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            merged = dict(metadata)
        else:
            merged = {}
        # Preserve top-level payload metadata fields for downstream filtering/citations.
        for key in ("knowledge_source_id", "source_type", "source_uri", "title", "domain", "label", "topic", "category", "language"):
            value = payload.get(key)
            if value is not None and key not in merged:
                merged[key] = value
        tags_value = payload.get("tags")
        if isinstance(tags_value, list) and "tags" not in merged:
            merged["tags"] = tags_value
        merged.setdefault("qdrant_point_id", point_id)
        return merged or None

    def _to_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _safe_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _safe_int(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        if number < 0:
            return None
        return number
