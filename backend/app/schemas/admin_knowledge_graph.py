"""Admin knowledge graph schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, conint, constr, field_validator

EntityType = Literal["person", "organization", "concept", "technology", "location", "other"]


class KnowledgeGraphEntityResponse(BaseModel):
    id: str
    name: constr(min_length=1, max_length=256)
    type: EntityType
    label: constr(min_length=1, max_length=128) | None = None
    domain: constr(min_length=1, max_length=128) | None = None
    description: str | None = None
    aliases: list[constr(min_length=1, max_length=256)] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_ids: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KnowledgeGraphRelationshipResponse(BaseModel):
    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: constr(min_length=1, max_length=128)
    label: constr(min_length=1, max_length=128) | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphNodeResponse(BaseModel):
    id: str
    label: constr(min_length=1, max_length=256)
    type: EntityType
    domain: constr(min_length=1, max_length=128) | None = None
    source_label: constr(min_length=1, max_length=128) | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphEdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    relation: constr(min_length=1, max_length=128)
    weight: float | None = Field(default=None, ge=0.0, le=1.0)
    source_label: constr(min_length=1, max_length=128) | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class PaginatedResultBase(BaseModel):
    total: conint(ge=0)
    page: conint(ge=1)
    page_size: conint(ge=1, le=200)
    total_pages: conint(ge=0)

    @staticmethod
    def build_total_pages(total: int, page_size: int) -> int:
        if total <= 0:
            return 0
        return int(ceil(total / page_size))


class KnowledgeGraphEntityListResponse(PaginatedResultBase):
    items: list[KnowledgeGraphEntityResponse] = Field(default_factory=list)


class KnowledgeGraphRelationshipListResponse(PaginatedResultBase):
    items: list[KnowledgeGraphRelationshipResponse] = Field(default_factory=list)


class KnowledgeGraphVisualizationResponse(BaseModel):
    nodes: list[KnowledgeGraphNodeResponse] = Field(default_factory=list)
    edges: list[KnowledgeGraphEdgeResponse] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphQueryFilters(BaseModel):
    page: conint(ge=1) = 1
    page_size: conint(ge=1, le=200) = 20
    label: constr(min_length=1, max_length=128) | None = None
    entity_type: EntityType | None = None
    search: constr(min_length=1, max_length=256) | None = None
    relationship_type: constr(min_length=1, max_length=128) | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("label", "search", "relationship_type")
    @classmethod
    def _normalize_string_filter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split())
        return normalized or None

    @field_validator("relationship_type")
    @classmethod
    def _normalize_relationship_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.upper()


class KnowledgeGraphVisualizationFilters(BaseModel):
    label: constr(min_length=1, max_length=128) | None = None
    entity_type: EntityType | None = None
    search: constr(min_length=1, max_length=256) | None = None
    relationship_type: constr(min_length=1, max_length=128) | None = None
    center_entity_id: constr(min_length=1, max_length=256) | None = None
    depth: conint(ge=1, le=3) = 2
    limit: conint(ge=1, le=500) = 150

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("label", "search", "relationship_type", "center_entity_id")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split())
        return normalized or None

    @field_validator("relationship_type")
    @classmethod
    def _normalize_rel_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.upper()
