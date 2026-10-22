"""RAG dependency contracts (ports).

Owns abstractions that RAG depends on.
Must not hardcode infrastructure clients in this layer.
"""

from __future__ import annotations

from typing import Protocol

from app.rag.schemas.context import RAGContextBundle
from app.rag.schemas.request import RAGQueryRequest
from app.rag.schemas.response import RAGAnswerResponse


class Retriever(Protocol):
    """Contract for retrieving candidate context items."""

    def retrieve(self, request: RAGQueryRequest) -> RAGContextBundle:
        """Return retrieved context bundle for the request."""


class Ranker(Protocol):
    """Contract for ordering retrieved candidates."""

    def rank(self, request: RAGQueryRequest, bundle: RAGContextBundle) -> RAGContextBundle:
        """Return ranked context bundle."""


class Generator(Protocol):
    """Contract for grounded answer generation."""

    def generate(self, request: RAGQueryRequest, bundle: RAGContextBundle) -> RAGAnswerResponse:
        """Return final answer payload."""
