"""RAG context bundle schema definitions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.rag.models.rag_types import TraceId
from app.rag.schemas.retrieval import GraphEvidence, RetrievalPlan, RetrievedChunk, RetrievedFact


class RAGContextBundle(BaseModel):
    """Combined retrieval context passed to ranking and generation."""

    trace_id: TraceId
    plan: RetrievalPlan
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    facts: list[RetrievedFact] = Field(default_factory=list)
    graph_evidence: list[GraphEvidence] = Field(default_factory=list)
    notes: str | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
