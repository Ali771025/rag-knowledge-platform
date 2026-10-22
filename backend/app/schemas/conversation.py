"""API schemas for conversation and session endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.conversation_memory.models import ConversationRole, ConversationState


class ChatAttachment(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=128)
    kind: Literal["image", "text", "document", "binary"] = "binary"
    extracted_text: str | None = Field(default=None, max_length=20_000)
    size_bytes: int = Field(default=0, ge=0)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ChatRequest(BaseModel):
    """Request payload for sending a chat message."""

    session_id: UUID | None = None
    message: str = Field(..., min_length=1, max_length=10_000)
    user_id: UUID | None = None
    knowledge_labels: list[str] | None = None
    memory_scope: str | None = Field(default=None, min_length=1, max_length=64)
    referral_invite_code: str | None = Field(default=None, min_length=4, max_length=128)
    attachments: list[ChatAttachment] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("knowledge_labels")
    @classmethod
    def _normalize_labels(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in value:
            label = " ".join(str(raw or "").strip().split()).lower()
            if not label:
                continue
            if label in seen:
                continue
            seen.add(label)
            normalized.append(label)
        return normalized

    @field_validator("memory_scope")
    @classmethod
    def _normalize_scope(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split()).lower()
        return normalized or None

    @field_validator("referral_invite_code")
    @classmethod
    def _normalize_referral_invite_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split()).upper()
        return normalized or None


class ChatResponse(BaseModel):
    """Response payload for a chat request."""

    session_id: UUID
    message: str = Field(..., min_length=0, max_length=10_000)
    state: ConversationState
    actions: list[str] = Field(default_factory=list)
    role: ConversationRole = ConversationRole.ASSISTANT
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")


class SessionCreateRequest(BaseModel):
    """Request payload for creating a new onboarding session."""

    user_id: UUID
    title: str | None = Field(default=None, min_length=1, max_length=255)
    initial_state: ConversationState = ConversationState.START
    metadata: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SessionResponse(BaseModel):
    """Response payload representing session state."""

    session_id: UUID
    user_id: UUID | None = None
    state: ConversationState
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class ErrorResponse(BaseModel):
    """Standard error response for conversation endpoints."""

    error: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=100)
    detail: str | None = Field(default=None, max_length=1_000)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# Backward-compatible aliases kept for Phase 1 references.
ConversationMessageCreate = ChatRequest
ConversationChatResponse = ChatResponse
