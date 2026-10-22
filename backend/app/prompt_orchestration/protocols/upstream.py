"""Upstream integration contracts for prompt orchestration.

These protocols define read-only context dependencies that this module consumes.
Concrete adapters should live in their owning modules and implement these ports.
"""

from __future__ import annotations

from typing import Protocol

from app.prompt_orchestration.models import (
    ConversationContextSnapshot,
    PromptOrchestrationRequest,
    RetrievalContextSnapshot,
    UserContextSnapshot,
)


class RetrievalContextProvider(Protocol):
    """Provides retrieval context snapshots from retrieval boundaries."""

    def get_retrieval_context(self, request: PromptOrchestrationRequest) -> RetrievalContextSnapshot:
        """Return retrieval context needed for prompt shaping."""


class ConversationContextProvider(Protocol):
    """Provides conversation-state snapshots from memory boundaries."""

    def get_conversation_context(self, request: PromptOrchestrationRequest) -> ConversationContextSnapshot:
        """Return conversation context needed for prompt shaping."""


class UserContextProvider(Protocol):
    """Provides user-context snapshots from user management boundaries."""

    def get_user_context(self, request: PromptOrchestrationRequest) -> UserContextSnapshot:
        """Return user context needed for prompt shaping."""
