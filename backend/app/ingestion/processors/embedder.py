"""Embedding processor."""

from __future__ import annotations

import logging
from typing import Any

from app.core.embedding_client import (
    EMBEDDING_MODEL,
    EmbeddingClient,
    EmbeddingClientAPIError,
    EmbeddingClientConfigurationError,
    EmbeddingClientError,
)
from app.ingestion.exceptions import ProcessorError
from app.ingestion.schemas import DocumentChunk, EmbeddedChunk

logger = logging.getLogger(__name__)

EXPECTED_VECTOR_DIMENSION = 3072


class EmbeddingProcessor:
    """Embeds chunks using configured embedding client."""

    def __init__(self, embedding_client: EmbeddingClient | None = None) -> None:
        self.embedding_client = embedding_client or EmbeddingClient(model=EMBEDDING_MODEL)

    def embed_chunk(self, chunk: DocumentChunk) -> EmbeddedChunk:
        """Embed a single chunk and return embedded chunk payload."""
        try:
            vector = self.embedding_client.embed_text(chunk.text)
            self._validate_dimension(vector, chunk_id=str(chunk.chunk_id))
            return self._build_embedded_chunk(chunk, vector)
        except (EmbeddingClientConfigurationError, EmbeddingClientAPIError, EmbeddingClientError) as exc:
            logger.error("embed_chunk_failed", extra={"chunk_id": str(chunk.chunk_id), "error": str(exc)})
            raise ProcessorError(f"failed to embed chunk {chunk.chunk_id}") from exc
        except Exception as exc:
            logger.exception("embed_chunk_unexpected_failure", exc_info=exc)
            raise ProcessorError(f"unexpected embedding failure for chunk {chunk.chunk_id}") from exc

    def embed_chunks(self, chunks: list[DocumentChunk]) -> list[EmbeddedChunk]:
        """Embed chunks in batch where possible."""
        if not chunks:
            return []
        texts = [chunk.text for chunk in chunks]
        try:
            vectors = self.embedding_client.embed_batch(texts)
            if len(vectors) != len(chunks):
                raise ProcessorError(
                    f"embedding result mismatch: expected {len(chunks)} vectors, received {len(vectors)}"
                )
            embedded_chunks: list[EmbeddedChunk] = []
            for chunk, vector in zip(chunks, vectors, strict=True):
                self._validate_dimension(vector, chunk_id=str(chunk.chunk_id))
                embedded_chunks.append(self._build_embedded_chunk(chunk, vector))
            logger.info("embed_chunks_success", extra={"count": len(embedded_chunks), "model": EMBEDDING_MODEL})
            return embedded_chunks
        except (EmbeddingClientConfigurationError, EmbeddingClientAPIError, EmbeddingClientError) as exc:
            logger.error("embed_chunks_failed", extra={"count": len(chunks), "error": str(exc)})
            raise ProcessorError("failed to embed chunk batch") from exc
        except Exception as exc:
            logger.exception("embed_chunks_unexpected_failure", exc_info=exc)
            if isinstance(exc, ProcessorError):
                raise
            raise ProcessorError("unexpected embedding batch failure") from exc

    def _build_embedded_chunk(self, chunk: DocumentChunk, vector: list[float]) -> EmbeddedChunk:
        metadata_json: dict[str, Any] = dict(chunk.metadata_json)
        metadata_json.update(
            {
                "embedding_attached": True,
                "embedding_model": EMBEDDING_MODEL,
                "embedding_dimension": len(vector),
            }
        )
        return EmbeddedChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            embedding_model=EMBEDDING_MODEL,
            vector=vector,
            metadata_json=metadata_json,
        )

    def _validate_dimension(self, vector: list[float], chunk_id: str) -> None:
        if len(vector) != EXPECTED_VECTOR_DIMENSION:
            raise ProcessorError(
                f"invalid embedding dimension for chunk {chunk_id}: "
                f"expected {EXPECTED_VECTOR_DIMENSION}, received {len(vector)}"
            )


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Backward-compatible helper used by earlier skeletons."""
    if not texts:
        return []
    processor = EmbeddingProcessor()
    try:
        return processor.embedding_client.embed_batch(texts)
    except Exception as exc:
        logger.error("embed_texts_helper_failed", extra={"count": len(texts), "error": str(exc)})
        raise
