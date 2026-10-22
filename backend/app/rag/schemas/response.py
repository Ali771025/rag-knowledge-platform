"""Outbound RAG response and grounding schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.rag.models.rag_types import ConfidenceLevel, RetrievalSource, TraceId


class CitationItem(BaseModel):
    """Citation entry mapped to retrieved evidence for source traceability."""

    citation_id: str
    trace_id: TraceId
    retrieval_source: RetrievalSource
    source_id: str
    snippet: str = Field(min_length=1)
    source_uri: str | None = None
    source_title: str | None = None
    label: str | None = None
    locator: str | None = None
    score: float | None = None
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class GroundingCheckResult(BaseModel):
    """Grounding validation result against cited evidence."""

    is_grounded: bool
    confidence_level: ConfidenceLevel
    checked_citation_ids: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    notes: str | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RAGAnswerResponse(BaseModel):
    """Final RAG answer payload with citations and confidence metadata."""

    trace_id: TraceId
    answer: str = Field(min_length=1)
    confidence_level: ConfidenceLevel
    citations: list[CitationItem] = Field(default_factory=list)
    grounding: GroundingCheckResult | None = None
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
