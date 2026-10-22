"""Base retriever scaffolding.

Owns retriever implementation shape.
Must not couple directly to API route or request parsing concerns.
"""

from __future__ import annotations

from app.rag.contracts import Retriever
from app.rag.schemas.context import RAGContextBundle
from app.rag.schemas.request import RAGQueryRequest


class BaseRetriever(Retriever):
    """Placeholder retriever base class."""

    def retrieve(self, request: RAGQueryRequest) -> RAGContextBundle:
        """Retrieve candidate contexts for the given request."""
        _ = request
        raise NotImplementedError("BaseRetriever.retrieve is scaffold-only for now.")
