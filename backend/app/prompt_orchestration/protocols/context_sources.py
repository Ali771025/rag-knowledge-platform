"""Protocols for structured context dependencies."""

from __future__ import annotations

from typing import Protocol

from app.prompt_orchestration.context_models import (
    MemorySummary,
    OnboardingState,
    PolicyConstraint,
    RecentMessage,
    RetrievedChunk,
    ToolResult,
    UserProfileSnapshot,
)
from app.prompt_orchestration.models import PromptOrchestrationRequest


class RetrievedChunkProvider(Protocol):
    """Provides authoritative retrieved chunks."""

    def get_retrieved_chunks(self, request: PromptOrchestrationRequest) -> tuple[RetrievedChunk, ...]:
        """Return retrieved chunks relevant to the user request."""


class MemoryContextProvider(Protocol):
    """Provides conversational continuity context."""

    def get_memory_summary(self, request: PromptOrchestrationRequest) -> MemorySummary | None:
        """Return the latest conversational memory summary."""

    def get_recent_messages(self, request: PromptOrchestrationRequest) -> tuple[RecentMessage, ...]:
        """Return recent conversation turns."""


class UserProfileContextProvider(Protocol):
    """Provides personalization context from user profile systems."""

    def get_user_profile(self, request: PromptOrchestrationRequest) -> UserProfileSnapshot | None:
        """Return user profile snapshot."""


class OnboardingStateProvider(Protocol):
    """Provides onboarding progress context."""

    def get_onboarding_state(self, request: PromptOrchestrationRequest) -> OnboardingState | None:
        """Return onboarding state snapshot."""


class PolicyConstraintProvider(Protocol):
    """Provides policy constraints applicable to the request."""

    def get_policy_constraints(self, request: PromptOrchestrationRequest) -> tuple[PolicyConstraint, ...]:
        """Return policy constraints for prompt building."""


class ToolResultProvider(Protocol):
    """Provides tool execution results for grounding."""

    def get_tool_results(self, request: PromptOrchestrationRequest) -> tuple[ToolResult, ...]:
        """Return recent tool results relevant to this request."""

