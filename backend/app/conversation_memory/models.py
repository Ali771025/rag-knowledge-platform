"""Core Pydantic models for conversation memory."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationRole(str, Enum):
    """Valid roles in a conversation turn."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationState(str, Enum):
    """Supported onboarding conversation states."""

    START = "start"
    INTRO = "intro"
    EDUCATION = "education"
    QNA = "qna"
    JOIN = "join"


class ConversationTurn(BaseModel):
    """A single message turn in a conversation."""

    role: ConversationRole
    message: str = Field(..., min_length=1, max_length=10_000)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class UserProfile(BaseModel):
    """Known user attributes used in memory and personalization."""

    user_id: UUID | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=320)
    preferences: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SessionState(BaseModel):
    """Session-level state tracked by the memory subsystem."""

    session_id: UUID
    state: ConversationState = ConversationState.START
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class ConversationContext(BaseModel):
    """Context object passed across memory components."""

    session_id: UUID
    state: ConversationState = ConversationState.START
    turns: list[ConversationTurn] = Field(default_factory=list)
    user_profile: UserProfile = Field(default_factory=UserProfile)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class ServiceResponse(BaseModel):
    """Standardized service response container for memory operations."""

    success: bool
    message: str = Field(..., min_length=1, max_length=1_000)
    state: ConversationState | None = None
    actions: list[str] = Field(default_factory=list)
    context: ConversationContext | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = Field(default=None, min_length=1, max_length=100)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConversationMemoryDecision(BaseModel):
    """Decision payload returned by memory policy evaluations."""

    next_state: ConversationState
    should_persist: bool
    actions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ResponseGenerationMetadata(BaseModel):
    """Structured metadata emitted by response generation components."""

    generator: str | None = Field(default=None, min_length=1, max_length=100)
    rag_used: bool | None = None
    model_name: str | None = Field(default=None, min_length=1, max_length=100)
    latency_ms: int | None = Field(default=None, ge=0)
    details: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConversationTraceMetadata(BaseModel):
    """Trace-friendly metadata for a conversation interaction lifecycle."""

    trace_id: str = Field(..., min_length=1, max_length=128)
    detected_intent: str | None = Field(default=None, min_length=1, max_length=100)
    previous_state: ConversationState | None = None
    new_state: ConversationState | None = None
    memory_policy_actions: list[str] = Field(default_factory=list)
    timestamps: dict[str, str] = Field(default_factory=dict)
    response_generation: ResponseGenerationMetadata | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# Backward-compatible aliases kept for Phase 1 references.
MemoryTurn = ConversationTurn
