"""Inbound RAG request schema definitions."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.rag.models.rag_types import RetrievalSource, TraceId


class RAGQueryRequest(BaseModel):
    """Normalized query request entering the RAG pipeline."""

    trace_id: TraceId = Field(default_factory=lambda: str(uuid4()))
    query: str = Field(min_length=1)
    user_id: str | None = None
    session_id: str | None = None
    conversation_id: str | None = None
    top_k: int = Field(default=8, ge=1, le=100)
    retrieval_sources: list[RetrievalSource] | None = None
    include_graph_evidence: bool = True
    filters: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
