"""Public RAG pipeline facade.

Owns end-to-end retrieval orchestration and grounded response assembly.
Must not implement source ingestion, graph-building, or HTTP endpoint concerns.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.rag.rag_orchestrator import RAGOrchestrator, RAGOrchestratorInput
from app.rag.schemas.request import RAGQueryRequest
from app.rag.schemas.response import RAGAnswerResponse


@dataclass
class RAGPipeline:
    """Backward-compatible facade over the production RAG orchestrator."""

    orchestrator: RAGOrchestrator = field(default_factory=RAGOrchestrator)

    def run(self, request: RAGQueryRequest) -> RAGAnswerResponse:
        """Execute the full retrieval, synthesis, grounding, and citation flow."""
        result = self.orchestrator.run(
            RAGOrchestratorInput(
                user_query=request.query,
                filters=request.filters,
                retrieval_sources=request.retrieval_sources,
                top_k=request.top_k,
                metadata=request.metadata,
            )
        )
        return result.response
