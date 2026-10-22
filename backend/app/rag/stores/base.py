"""Base store scaffolding.

Owns abstract data-access shape used by retrievers.
Must not include ranking or generation logic.
"""

from __future__ import annotations

from typing import Protocol

from app.rag.models.rag_types import RetrievalSource
from app.rag.schemas.retrieval import RetrievedChunk


class ContextStore(Protocol):
    """Contract for loading candidate context items from storage."""

    def search(self, query: str, top_k: int, source: RetrievalSource) -> list[RetrievedChunk]:
        """Return storage-level candidate contexts for query text."""
