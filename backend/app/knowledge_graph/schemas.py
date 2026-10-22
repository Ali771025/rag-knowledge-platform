"""Internal knowledge graph schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, conint, constr


class GraphEntity(BaseModel):
    """Normalized graph entity."""

    entity_id: UUID = Field(default_factory=uuid4)
    name: constr(min_length=1, max_length=256)
    entity_type: Literal["person", "organization", "concept", "technology", "location", "other"]
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    aliases: list[constr(min_length=1, max_length=256)] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class GraphRelation(BaseModel):
    """Directed relation between two entities."""

    relation_id: UUID = Field(default_factory=uuid4)
    source_entity_id: UUID
    target_entity_id: UUID
    relation_type: constr(min_length=1, max_length=128)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: constr(min_length=1) | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class GraphPath(BaseModel):
    """Path through graph entities and relations."""

    path_id: UUID = Field(default_factory=uuid4)
    entity_ids: list[UUID] = Field(default_factory=list)
    relation_ids: list[UUID] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=0.0)


class GraphContext(BaseModel):
    """Graph retrieval context for downstream generation."""

    query: constr(min_length=1, max_length=2000)
    entities: list[GraphEntity] = Field(default_factory=list)
    relations: list[GraphRelation] = Field(default_factory=list)
    paths: list[GraphPath] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class EntityExtractionResult(BaseModel):
    """Result of entity extraction stage."""

    document_id: UUID
    chunk_id: UUID | None = None
    entities: list[GraphEntity] = Field(default_factory=list)
    model_name: constr(min_length=1, max_length=128) | None = None
    latency_ms: conint(ge=0) | None = None
    status: Literal["pending", "running", "completed", "failed"] = "completed"
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")


class RelationExtractionResult(BaseModel):
    """Result of relation extraction stage."""

    document_id: UUID
    chunk_id: UUID | None = None
    relations: list[GraphRelation] = Field(default_factory=list)
    model_name: constr(min_length=1, max_length=128) | None = None
    latency_ms: conint(ge=0) | None = None
    status: Literal["pending", "running", "completed", "failed"] = "completed"
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")


# Backward-compatible aliases used by earlier phase skeletons.
class GraphBuildRequest(BaseModel):
    """Compatibility request schema for graph pipeline trigger."""

    document_id: UUID
    chunk_ids: list[UUID] = Field(default_factory=list)


class GraphBuildResult(BaseModel):
    """Compatibility result schema for graph pipeline trigger."""

    document_id: UUID
    entities: int
    relations: int
    status: Literal["pending", "running", "completed", "failed"]
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
