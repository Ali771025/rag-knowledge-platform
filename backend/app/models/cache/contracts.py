"""Shared cache-layer typed contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class CachedResponse(BaseModel):
    """Serializable cache entry payload for response reuse."""

    cache_key: str = Field(..., min_length=1, max_length=512)
    namespace: str = Field(..., min_length=1, max_length=128)
    payload: dict[str, Any] | list[Any] | str | int | float | bool | None
    ttl_seconds: int | None = Field(default=None, ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SemanticCacheLookupResult(BaseModel):
    """Outcome of a semantic cache lookup operation."""

    hit: bool
    cache_key: str = Field(..., min_length=1, max_length=512)
    similarity_score: float | None = Field(default=None, ge=0.0, le=1.0)
    response: CachedResponse | None = None
    reason: str | None = Field(default=None, min_length=1, max_length=256)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RAGCacheResult(BaseModel):
    """Outcome of a retrieval-augmented cache lookup."""

    hit: bool
    cache_key: str = Field(..., min_length=1, max_length=512)
    response: CachedResponse | None = None
    source_document_ids: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SessionContextPayload(BaseModel):
    """Session-scoped context payload suitable for JSON/Redis storage."""

    session_id: str = Field(..., min_length=1, max_length=128)
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    recent_messages: list[dict[str, Any]] = Field(
        default_factory=list,
        validation_alias=AliasChoices("recent_messages", "conversation_turns"),
    )
    dialogue_state: str | None = Field(default=None, min_length=1, max_length=128)
    onboarding_step: str | None = Field(default=None, min_length=1, max_length=128)
    user_profile_snapshot: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)
    last_updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        validation_alias=AliasChoices("last_updated_at", "updated_at"),
    )

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CacheInvalidateResult(BaseModel):
    """Result of invalidating one key or a namespace scope."""

    success: bool
    namespace: str = Field(..., min_length=1, max_length=128)
    cache_key: str | None = Field(default=None, min_length=1, max_length=512)
    invalidated_count: int = Field(default=0, ge=0)
    invalidated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: str | None = Field(default=None, min_length=1, max_length=512)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
