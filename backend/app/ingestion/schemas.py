"""Internal ingestion schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, conint, constr


class SourceConfig(BaseModel):
    """Source-specific ingestion configuration."""

    source_type: Literal["web", "discord", "file", "docs"]
    source_uri: constr(min_length=1, max_length=2048)
    timeout_seconds: conint(ge=1, le=300) = 30
    max_items: conint(ge=1, le=100000) = 1000
    options: dict[str, Any] = Field(default_factory=dict)


class RawDocument(BaseModel):
    """Raw source document before processing."""

    document_id: UUID = Field(default_factory=uuid4)
    source_type: Literal["web", "discord", "file", "docs"]
    source_uri: constr(min_length=1, max_length=2048)
    title: constr(min_length=1, max_length=512) | None = None
    raw_content: constr(min_length=1)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CleanedDocument(BaseModel):
    """Normalized/cleaned document content."""

    document_id: UUID
    cleaned_text: constr(min_length=1)
    language: constr(min_length=2, max_length=16) | None = None
    summary: constr(min_length=1, max_length=4000) | None = None
    content_hash: constr(min_length=8, max_length=128)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """Chunked document segment before embedding."""

    chunk_id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    chunk_index: conint(ge=0)
    text: constr(min_length=1)
    token_count: conint(ge=0) | None = None
    content_hash: constr(min_length=8, max_length=128)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class EmbeddedChunk(BaseModel):
    """Chunk with embedding vector attached."""

    chunk_id: UUID
    document_id: UUID
    chunk_index: conint(ge=0)
    text: constr(min_length=1)
    embedding_model: constr(min_length=1, max_length=128)
    vector: list[float] = Field(min_length=1)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class IngestionPipelineResult(BaseModel):
    """Final pipeline output state."""

    job_id: UUID
    status: Literal["pending", "running", "completed", "failed", "partial"]
    document_id: UUID | None = None
    chunks_total: conint(ge=0) = 0
    chunks_embedded: conint(ge=0) = 0
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")


# Backward-compatible aliases used by earlier phase skeletons.
class IngestionRequest(BaseModel):
    """Compatibility request schema for existing ingestion pipeline skeletons."""

    job_id: UUID = Field(default_factory=uuid4)
    source_type: Literal["web", "discord", "file", "docs"]
    source_uri: constr(min_length=1, max_length=2048)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionChunk(BaseModel):
    """Compatibility chunk schema for existing ingestion pipeline skeletons."""

    chunk_id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    content: constr(min_length=1)
    sequence: conint(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionResult(BaseModel):
    """Compatibility result schema for existing ingestion pipeline skeletons."""

    job_id: UUID
    status: Literal["pending", "running", "completed", "failed", "partial"]
    processed_chunks: conint(ge=0) = 0
    errors: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
