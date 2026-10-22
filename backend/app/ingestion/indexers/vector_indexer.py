"""Qdrant vector indexer."""

from __future__ import annotations

import logging
import os
from typing import Any

from app.core.qdrant_client import QdrantAPIError, QdrantClientAdapter, VECTOR_SIZE
from app.core.vector_payload import QDRANT_CHUNK_TEXT_KEY, QDRANT_CHUNK_TEXT_LEGACY_KEY
from app.ingestion.exceptions import IndexerError
from app.ingestion.schemas import EmbeddedChunk, IngestionChunk

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = int(os.getenv("QDRANT_UPSERT_BATCH_SIZE", "128"))


class VectorIndexerError(IndexerError):
    """Raised when vector indexing operations fail."""


class VectorIndexer:
    """Indexes embedded chunks into Qdrant collection `knowledge_base`."""

    def __init__(self, qdrant_client: QdrantClientAdapter | None = None, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
        self.qdrant_client = qdrant_client or QdrantClientAdapter()
        self.batch_size = max(1, batch_size)

    def index_chunk(self, chunk: EmbeddedChunk) -> None:
        """Index a single embedded chunk."""
        self._validate_vector(chunk)
        payload_item = self._build_upsert_item(chunk)
        try:
            self.qdrant_client.ensure_collection()
            self.qdrant_client.upsert_vectors([payload_item])
            logger.info("vector_index_chunk_success", extra={"chunk_id": str(chunk.chunk_id)})
        except Exception as exc:
            logger.exception("vector_index_chunk_failed", exc_info=exc)
            raise VectorIndexerError(f"failed to index chunk {chunk.chunk_id}") from exc

    def index_chunks(self, chunks: list[EmbeddedChunk]) -> None:
        """Batch index embedded chunks with partial-failure handling."""
        if not chunks:
            return
        self.qdrant_client.ensure_collection()

        failures: list[str] = []
        valid_chunks: list[EmbeddedChunk] = []
        for chunk in chunks:
            try:
                self._validate_vector(chunk)
                valid_chunks.append(chunk)
            except Exception as exc:
                logger.error(
                    "vector_index_chunk_validation_failed",
                    extra={"chunk_id": str(chunk.chunk_id), "error": str(exc)},
                )
                failures.append(str(chunk.chunk_id))

        for start in range(0, len(valid_chunks), self.batch_size):
            batch = valid_chunks[start : start + self.batch_size]
            items = [self._build_upsert_item(chunk) for chunk in batch]
            try:
                self.qdrant_client.upsert_vectors(items)
                logger.info("vector_index_batch_success", extra={"batch_size": len(batch)})
            except Exception as batch_exc:
                logger.warning(
                    "vector_index_batch_failed_retrying_individual",
                    extra={"batch_size": len(batch), "error": str(batch_exc)},
                )
                for chunk in batch:
                    try:
                        self.qdrant_client.upsert_vectors([self._build_upsert_item(chunk)])
                    except Exception as item_exc:
                        logger.error(
                            "vector_index_partial_failure",
                            extra={"chunk_id": str(chunk.chunk_id), "error": str(item_exc)},
                        )
                        failures.append(str(chunk.chunk_id))

        if failures:
            raise VectorIndexerError(
                f"partial vector indexing failure for {len(failures)} chunks",
            )

    def delete_chunks(self, chunk_ids: list[str]) -> None:
        """Delete indexed chunks by chunk IDs."""
        if not chunk_ids:
            return
        try:
            self.qdrant_client.ensure_collection()
            self.qdrant_client.delete_vectors(chunk_ids)
            logger.info("vector_index_delete_success", extra={"count": len(chunk_ids)})
        except Exception as exc:
            logger.exception("vector_index_delete_failed", exc_info=exc)
            raise VectorIndexerError("failed to delete chunk vectors") from exc

    async def index(self, chunks: list[IngestionChunk]) -> int:
        """Backward-compatible method for earlier skeleton usage."""
        logger.info("vector_index_compat_invoked", extra={"chunk_count": len(chunks)})
        return len(chunks)

    def _validate_vector(self, chunk: EmbeddedChunk) -> None:
        vector = chunk.vector
        if not vector:
            raise VectorIndexerError(f"chunk {chunk.chunk_id} has empty embedding vector")
        if len(vector) != VECTOR_SIZE:
            raise VectorIndexerError(
                f"chunk {chunk.chunk_id} has invalid vector dimension {len(vector)} (expected {VECTOR_SIZE})"
            )

    def _build_upsert_item(self, chunk: EmbeddedChunk) -> dict[str, Any]:
        metadata = dict(chunk.metadata_json or {})
        source_id = metadata.get("source_id")
        if source_id is None:
            document_id = metadata.get("document_id") or str(chunk.document_id)
            source_id = f"document:{document_id}"
        payload = {
            "chunk_id": str(chunk.chunk_id),
            "document_id": str(chunk.document_id),
            "source_id": source_id,
            QDRANT_CHUNK_TEXT_KEY: chunk.text,
            QDRANT_CHUNK_TEXT_LEGACY_KEY: chunk.text,
            "knowledge_source_id": metadata.get("knowledge_source_id"),
            "source_type": metadata.get("source_type"),
            "source_uri": metadata.get("source_uri"),
            "title": metadata.get("title"),
            "domain": metadata.get("domain"),
            "label": metadata.get("label"),
            "topic": metadata.get("topic"),
            "category": metadata.get("category"),
            "tags": metadata.get("tags", []),
            "language": metadata.get("language"),
            "position_index": metadata.get("position_index", chunk.chunk_index),
        }
        return {"id": str(chunk.chunk_id), "vector": chunk.vector, "payload": payload}
