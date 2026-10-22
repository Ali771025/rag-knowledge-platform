"""Retrieval planning and evidence schemas with source traceability."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.rag.models.rag_types import (
    ChunkId,
    FactId,
    GraphEvidenceId,
    RetrievalSource,
    SourceId,
    TraceId,
)


class RetrievalPlan(BaseModel):
    """Execution plan for retrieval across selected sources."""

    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    trace_id: TraceId
    sources: list[RetrievalSource] = Field(min_length=1)
    source_weights: dict[RetrievalSource, float] | None = None
    top_k_per_source: dict[RetrievalSource, int] | None = None
    include_chunks: bool = True
    include_facts: bool = True
    include_graph_evidence: bool = True
    filters: dict[str, Any] | None = None
    constraints: dict[str, Any] | None = None
    notes: str | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RetrievedChunk(BaseModel):
    """Text chunk candidate returned by retrieval with trace metadata."""

    chunk_id: ChunkId
    trace_id: TraceId
    retrieval_source: RetrievalSource
    source_id: SourceId
    document_id: str
    content: str = Field(min_length=1)
    score: float | None = None
    rank: int | None = Field(default=None, ge=1)
    source_uri: str | None = None
    source_title: str | None = None
    start_char: int | None = Field(default=None, ge=0)
    end_char: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RetrievedFact(BaseModel):
    """Structured fact candidate returned by retrieval with trace metadata."""

    fact_id: FactId
    trace_id: TraceId
    retrieval_source: RetrievalSource
    source_id: SourceId
    subject: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    obj: str = Field(min_length=1)
    score: float | None = None
    source_uri: str | None = None
    source_title: str | None = None
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class GraphEvidence(BaseModel):
    """Graph-derived evidence path with source traceability."""

    evidence_id: GraphEvidenceId
    trace_id: TraceId
    retrieval_source: RetrievalSource
    source_id: SourceId
    node_ids: list[str] = Field(min_length=1)
    edge_ids: list[str] | None = None
    path_summary: str = Field(min_length=1)
    score: float | None = None
    source_uri: str | None = None
    source_title: str | None = None
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
