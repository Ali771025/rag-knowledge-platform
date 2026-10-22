"""Public knowledge graph API schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, conint, constr


class QueryExpansionRequest(BaseModel):
    """Request payload for graph query expansion."""

    query: constr(min_length=1, max_length=2000)
    max_expansions: conint(ge=1, le=50) = 10
    include_synonyms: bool = True

    model_config = ConfigDict(extra="forbid")


class QueryExpansionResponse(BaseModel):
    """Response payload for query expansion."""

    query: str
    expansions: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class GraphContextRequest(BaseModel):
    """Request payload for graph context retrieval."""

    query: constr(min_length=1, max_length=2000)
    top_k_entities: conint(ge=1, le=100) = 20
    top_k_relations: conint(ge=1, le=200) = 50
    include_paths: bool = True

    model_config = ConfigDict(extra="forbid")


class GraphContextResponse(BaseModel):
    """Response payload containing graph context."""

    query: str
    entities: list[dict[str, Any]] = Field(default_factory=list)
    relations: list[dict[str, Any]] = Field(default_factory=list)
    paths: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata_json: dict[str, Any] = Field(default_factory=dict)


# Backward-compatible schemas used by existing endpoint skeletons.
class GraphBuildRequestSchema(BaseModel):
    """Compatibility request schema for graph build endpoint skeleton."""

    document_id: UUID


class GraphBuildResponseSchema(BaseModel):
    """Compatibility response schema for graph build endpoint skeleton."""

    document_id: UUID
    status: str
