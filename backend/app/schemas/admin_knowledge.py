"""Admin knowledge management schemas."""

from __future__ import annotations

from datetime import datetime
from math import ceil
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, conint, constr

KnowledgeSourceType = Literal["file", "url"]
IngestionStatus = Literal["pending", "in_progress", "completed", "failed"]
IngestionStep = Literal["uploaded", "parsing", "chunking", "embedding", "indexing", "completed", "failed"]


class IngestionStepStatusResponse(BaseModel):
    step: IngestionStep
    status: IngestionStatus
    message: str | None = None
    progress: conint(ge=0, le=100) | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class KnowledgeSourceResponse(BaseModel):
    id: UUID
    name: constr(min_length=1, max_length=512)
    type: KnowledgeSourceType
    domain: constr(min_length=1, max_length=128)
    label: constr(min_length=1, max_length=128)
    tags: list[constr(min_length=1, max_length=64)] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    status: IngestionStatus
    total_chunks: conint(ge=0) = 0
    embedded_chunks: conint(ge=0) = 0
    indexing_completed: bool = False
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)


class KnowledgeSourceStatusResponse(BaseModel):
    source_id: UUID
    status: IngestionStatus
    steps: list[IngestionStepStatusResponse] = Field(default_factory=list)
    total_chunks: conint(ge=0) = 0
    embedded_chunks: conint(ge=0) = 0
    indexing_completed: bool = False
    last_updated_at: datetime


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


class KnowledgeSourceListResponse(PaginatedResultBase):
    items: list[KnowledgeSourceResponse] = Field(default_factory=list)


class CreateKnowledgeSourceFromUrlRequest(BaseModel):
    url: HttpUrl
    domain: constr(min_length=1, max_length=128)
    label: constr(min_length=1, max_length=128)
    tags: list[constr(min_length=1, max_length=64)] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class UpdateKnowledgeLabelRequest(BaseModel):
    label: constr(min_length=1, max_length=128)

    model_config = ConfigDict(extra="forbid")


class BulkSourceActionRequest(BaseModel):
    source_ids: list[UUID] = Field(min_length=1, max_length=500)

    model_config = ConfigDict(extra="forbid")


class BulkSourceActionResponse(BaseModel):
    requested: conint(ge=0)
    processed: conint(ge=0)
    failed_source_ids: list[UUID] = Field(default_factory=list)
