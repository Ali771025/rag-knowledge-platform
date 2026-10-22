"""Public ingestion API schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, conint, constr


class UrlIngestionRequest(BaseModel):
    """Request payload for URL-based ingestion."""

    source_type: Literal["web"] = "web"
    url: HttpUrl
    title: constr(min_length=1, max_length=512) | None = None
    tags: list[constr(min_length=1, max_length=64)] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class DiscordIngestionRequest(BaseModel):
    """Request payload for Discord ingestion."""

    source_type: Literal["discord"] = "discord"
    guild_id: constr(min_length=1, max_length=128)
    channel_id: constr(min_length=1, max_length=128)
    message_limit: conint(ge=1, le=10000) = 500
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class FileIngestionRequest(BaseModel):
    """Request payload for file ingestion."""

    source_type: Literal["file"] = "file"
    file_path: constr(min_length=1, max_length=2048)
    file_name: constr(min_length=1, max_length=512) | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class IngestionResponse(BaseModel):
    """Response payload for ingestion request submission/status."""

    job_id: UUID
    status: Literal["pending", "running", "completed", "failed", "partial"]
    source_type: Literal["web", "discord", "file", "docs"]
    source_uri: constr(min_length=1, max_length=2048)
    message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


# Backward-compatible aliases used by existing endpoint skeletons.
IngestionStartRequest = UrlIngestionRequest
IngestionStartResponse = IngestionResponse
