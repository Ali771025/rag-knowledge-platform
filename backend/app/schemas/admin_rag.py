"""Admin RAG config and retrieval test schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EmbeddingModel = Literal["text-embedding-3-large", "bge-m3"]


class AdminRAGConfig(BaseModel):
    chunk_size: int = Field(default=900, ge=128, le=8192)
    chunk_overlap: int = Field(default=120, ge=0, le=2048)
    top_k: int = Field(default=12, ge=1, le=100)
    similarity_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    reranker_enabled: bool = True
    hybrid_search_enabled: bool = True
    graph_enhanced_retrieval_enabled: bool = True
    embedding_model: EmbeddingModel = "text-embedding-3-large"
    reranker_model: str = Field(default="heuristic-v1", min_length=1, max_length=255)
    vector_collection_name: str = Field(default="knowledge_base", min_length=1, max_length=255)
    default_labels: list[str] = Field(default_factory=list, max_length=50)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("default_labels")
    @classmethod
    def _normalize_labels(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for label in value:
            cleaned = " ".join(str(label or "").strip().split()).lower()
            if not cleaned:
                continue
            if len(cleaned) > 128:
                raise ValueError("default_labels items must be <= 128 chars")
            if cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)
        return normalized

    @field_validator("chunk_overlap")
    @classmethod
    def _validate_overlap(cls, value: int, info):  # type: ignore[no-untyped-def]
        chunk_size = info.data.get("chunk_size")
        if isinstance(chunk_size, int) and value >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return value


class AdminRAGTestRequest(BaseModel):
    query: str = Field(min_length=1, max_length=5000)
    domain: str | None = Field(default=None, min_length=1, max_length=128)
    labels: list[str] | None = Field(default=None, max_length=50)
    source_ids: list[str] | None = Field(default=None, max_length=200)
    top_k: int | None = Field(default=None, ge=1, le=100)
    similarity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    reranker_enabled: bool | None = None
    hybrid_search_enabled: bool | None = None
    graph_enhanced_retrieval_enabled: bool | None = None
    include_graph_context: bool = False

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("labels")
    @classmethod
    def _normalize_test_labels(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for label in value:
            cleaned = " ".join(str(label or "").strip().split()).lower()
            if not cleaned:
                continue
            if len(cleaned) > 128:
                raise ValueError("labels items must be <= 128 chars")
            if cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)
        return normalized


class AdminRAGRetrievedChunk(BaseModel):
    chunk_id: str
    source_id: str
    source_title: str | None = None
    label: str | None = None
    content: str
    score: float | None = None
    rerank_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class AdminRAGCitation(BaseModel):
    source_id: str
    source_title: str | None = None
    label: str | None = None
    chunk_id: str | None = None
    locator: str | None = None
    score: float | None = None
    snippet: str

    model_config = ConfigDict(extra="forbid")


class AdminRAGDiagnostics(BaseModel):
    timings_ms: dict[str, int] = Field(default_factory=dict)
    flags: dict[str, bool] = Field(default_factory=dict)
    retrieval_summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class AdminRAGTestResult(BaseModel):
    query: str
    config_used: AdminRAGConfig
    retrieved_chunks: list[AdminRAGRetrievedChunk] = Field(default_factory=list)
    reranked_chunks: list[AdminRAGRetrievedChunk] | None = None
    final_answer: str
    citations: list[AdminRAGCitation] = Field(default_factory=list)
    diagnostics: AdminRAGDiagnostics
    latency_ms: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")
