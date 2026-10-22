"""Base generator scaffolding.

Owns answer generator implementation shape.
Must not manage long-term conversation state.
"""

from __future__ import annotations

from app.rag.contracts import Generator
from app.rag.schemas.context import RAGContextBundle
from app.rag.schemas.request import RAGQueryRequest
from app.rag.schemas.response import RAGAnswerResponse


class BaseGenerator(Generator):
    """Placeholder generator base class."""

    def generate(self, request: RAGQueryRequest, bundle: RAGContextBundle) -> RAGAnswerResponse:
        """Generate an answer using the request and ranked contexts."""
        _ = (request, bundle)
        raise NotImplementedError("BaseGenerator.generate is scaffold-only for now.")
