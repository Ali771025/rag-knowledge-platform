"""Public document API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, conint, constr


class ChunkResponse(BaseModel):
    """Chunk representation for API responses."""

    id: UUID
    document_id: UUID
    chunk_index: conint(ge=0)
    text: str
    token_count: conint(ge=0) | None = None
    embedding_model: constr(min_length=1, max_length=128) | None = None
    content_hash: constr(min_length=8, max_length=128) | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    """Document representation for API responses."""

    id: UUID
    source_type: Literal["web", "discord", "file", "docs"]
    source_uri: constr(min_length=1, max_length=2048)
    title: constr(min_length=1, max_length=512) | None = None
    language: constr(min_length=2, max_length=16) | None = None
    summary: str | None = None
    content_hash: constr(min_length=8, max_length=128) | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    chunks: list[ChunkResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# Backward-compatible alias used by existing endpoint/model skeletons.
DocumentRead = DocumentResponse
