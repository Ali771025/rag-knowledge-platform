"""Structured context contracts for prompt orchestration dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID

from app.prompt_orchestration.exceptions import PromptContractError
from app.prompt_orchestration.models import PromptMessage


def _validate_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise PromptContractError(f"`{field_name}` must be a non-empty string.")
    return normalized


def _validate_optional_non_empty(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise PromptContractError(f"`{field_name}` cannot be blank when provided.")
    return normalized


def _to_frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


class ContextTrustLevel(StrEnum):
    """Trust boundary categories for context sources."""

    AUTHORITATIVE = "authoritative"
    CONVERSATIONAL = "conversational"
    PERSONALIZATION = "personalization"


class OnboardingStage(StrEnum):
    """High-level onboarding progression."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ConstraintStrength(StrEnum):
    """Strength of policy constraints."""

    HARD = "hard"
    SOFT = "soft"


class ToolResultStatus(StrEnum):
    """Normalized outcome for tool calls."""

    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """Retrieved document chunk usable as grounding context."""

    chunk_id: str
    source_id: str
    content: str
    relevance_score: float
    citation: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    trust_level: ContextTrustLevel = ContextTrustLevel.AUTHORITATIVE

    def __post_init__(self) -> None:
        object.__setattr__(self, "chunk_id", _validate_non_empty(self.chunk_id, "chunk_id"))
        object.__setattr__(self, "source_id", _validate_non_empty(self.source_id, "source_id"))
        object.__setattr__(self, "content", _validate_non_empty(self.content, "content"))
        object.__setattr__(self, "citation", _validate_optional_non_empty(self.citation, "citation"))
        if self.relevance_score < 0 or self.relevance_score > 1:
            raise PromptContractError("`relevance_score` must be between 0 and 1.")
        if self.trust_level is not ContextTrustLevel.AUTHORITATIVE:
            raise PromptContractError("`RetrievedChunk` must use authoritative trust level.")
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class MemorySummary:
    """Conversation-level memory summary."""

    summary: str
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    trust_level: ContextTrustLevel = ContextTrustLevel.CONVERSATIONAL

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", _validate_non_empty(self.summary, "summary"))
        if self.updated_at.tzinfo is None:
            raise PromptContractError("`updated_at` must be timezone-aware.")
        if self.trust_level is not ContextTrustLevel.CONVERSATIONAL:
            raise PromptContractError("`MemorySummary` must use conversational trust level.")


@dataclass(frozen=True, slots=True)
class RecentMessage:
    """Recent conversational message with minimal metadata."""

    message: PromptMessage
    occurred_at: datetime | None = None
    trust_level: ContextTrustLevel = ContextTrustLevel.CONVERSATIONAL

    def __post_init__(self) -> None:
        if self.occurred_at is not None and self.occurred_at.tzinfo is None:
            raise PromptContractError("`occurred_at` must be timezone-aware when provided.")
        if self.trust_level is not ContextTrustLevel.CONVERSATIONAL:
            raise PromptContractError("`RecentMessage` must use conversational trust level.")


@dataclass(frozen=True, slots=True)
class UserProfileSnapshot:
    """Minimal personalization context for a user."""

    user_id: UUID | None
    preferred_language: str | None = None
    tone_preference: str | None = None
    expertise_level: str | None = None
    preferences: Mapping[str, Any] = field(default_factory=dict)
    trust_level: ContextTrustLevel = ContextTrustLevel.PERSONALIZATION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "preferred_language",
            self.preferred_language.strip().lower() if self.preferred_language else None,
        )
        object.__setattr__(self, "tone_preference", _validate_optional_non_empty(self.tone_preference, "tone_preference"))
        object.__setattr__(self, "expertise_level", _validate_optional_non_empty(self.expertise_level, "expertise_level"))
        object.__setattr__(self, "preferences", _to_frozen_mapping(self.preferences))
        if self.trust_level is not ContextTrustLevel.PERSONALIZATION:
            raise PromptContractError("`UserProfileSnapshot` must use personalization trust level.")


@dataclass(frozen=True, slots=True)
class OnboardingState:
    """Structured onboarding progress state."""

    stage: OnboardingStage
    completed_steps: tuple[str, ...] = ()
    pending_steps: tuple[str, ...] = ()
    last_completed_step: str | None = None
    trust_level: ContextTrustLevel = ContextTrustLevel.AUTHORITATIVE

    def __post_init__(self) -> None:
        completed = tuple(_validate_non_empty(step, "completed_steps[]") for step in self.completed_steps)
        pending = tuple(_validate_non_empty(step, "pending_steps[]") for step in self.pending_steps)
        overlap = set(completed).intersection(pending)
        if overlap:
            overlap_str = ", ".join(sorted(overlap))
            raise PromptContractError(f"Onboarding steps cannot be both completed and pending: {overlap_str}")
        object.__setattr__(self, "completed_steps", completed)
        object.__setattr__(self, "pending_steps", pending)
        object.__setattr__(self, "last_completed_step", _validate_optional_non_empty(self.last_completed_step, "last_completed_step"))
        if self.trust_level is not ContextTrustLevel.AUTHORITATIVE:
            raise PromptContractError("`OnboardingState` must use authoritative trust level.")


@dataclass(frozen=True, slots=True)
class PolicyConstraint:
    """Policy guardrail applied to the response."""

    constraint_id: str
    instruction: str
    strength: ConstraintStrength = ConstraintStrength.HARD
    source: str | None = None
    trust_level: ContextTrustLevel = ContextTrustLevel.AUTHORITATIVE

    def __post_init__(self) -> None:
        object.__setattr__(self, "constraint_id", _validate_non_empty(self.constraint_id, "constraint_id"))
        object.__setattr__(self, "instruction", _validate_non_empty(self.instruction, "instruction"))
        object.__setattr__(self, "source", _validate_optional_non_empty(self.source, "source"))
        if self.trust_level is not ContextTrustLevel.AUTHORITATIVE:
            raise PromptContractError("`PolicyConstraint` must use authoritative trust level.")


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Normalized tool execution output for prompt grounding."""

    tool_name: str
    status: ToolResultStatus
    summary: str
    output_payload: Mapping[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    trust_level: ContextTrustLevel = ContextTrustLevel.AUTHORITATIVE

    def __post_init__(self) -> None:
        object.__setattr__(self, "tool_name", _validate_non_empty(self.tool_name, "tool_name"))
        object.__setattr__(self, "summary", _validate_non_empty(self.summary, "summary"))
        object.__setattr__(self, "error_message", _validate_optional_non_empty(self.error_message, "error_message"))
        object.__setattr__(self, "output_payload", _to_frozen_mapping(self.output_payload))

        if self.status is ToolResultStatus.ERROR and self.error_message is None:
            raise PromptContractError("`error_message` is required when tool result status is `error`.")
        if self.trust_level is not ContextTrustLevel.AUTHORITATIVE:
            raise PromptContractError("`ToolResult` must use authoritative trust level.")


@dataclass(frozen=True, slots=True)
class AuthoritativeContext:
    """Context bundle for authoritative grounding signals."""

    retrieved_chunks: tuple[RetrievedChunk, ...] = ()
    onboarding_state: OnboardingState | None = None
    policy_constraints: tuple[PolicyConstraint, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()


@dataclass(frozen=True, slots=True)
class ConversationalContext:
    """Context bundle for dialogue continuity signals."""

    memory_summary: MemorySummary | None = None
    recent_messages: tuple[RecentMessage, ...] = ()


@dataclass(frozen=True, slots=True)
class PersonalizationContext:
    """Context bundle for user-specific personalization signals."""

    user_profile: UserProfileSnapshot | None = None


@dataclass(frozen=True, slots=True)
class PromptContextEnvelope:
    """Top-level structured context contract for prompt orchestration."""

    authoritative: AuthoritativeContext = field(default_factory=AuthoritativeContext)
    conversational: ConversationalContext = field(default_factory=ConversationalContext)
    personalization: PersonalizationContext = field(default_factory=PersonalizationContext)
