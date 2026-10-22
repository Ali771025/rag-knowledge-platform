"""Base ranker scaffolding.

Owns ranking implementation shape.
Must not own persistence of source documents.
"""

from __future__ import annotations

from app.rag.contracts import Ranker
from app.rag.schemas.context import RAGContextBundle
from app.rag.schemas.request import RAGQueryRequest


class BaseRanker(Ranker):
    """Placeholder ranker base class."""

    def rank(self, request: RAGQueryRequest, bundle: RAGContextBundle) -> RAGContextBundle:
        """Rank retrieved contexts for the given request."""
        _ = (request, bundle)
        raise NotImplementedError("BaseRanker.rank is scaffold-only for now.")
