"""Custom exceptions for the conversation memory module."""


class ConversationMemoryError(Exception):
    """Base exception for conversation memory failures."""

    def __init__(self, message: str = "Conversation memory error") -> None:
        super().__init__(message)

class SessionNotFoundError(ConversationMemoryError):
    """Raised when a session cannot be found in memory or storage."""


class InvalidSessionStateError(ConversationMemoryError):
    """Raised when session state is invalid for the requested operation."""


class RedisRepositoryError(ConversationMemoryError):
    """Raised when Redis-backed memory operations fail."""


class PostgresRepositoryError(ConversationMemoryError):
    """Raised when PostgreSQL-backed memory operations fail."""


class IntentDetectionError(ConversationMemoryError):
    """Raised when intent detection fails or produces invalid output."""


class ContextBuildError(ConversationMemoryError):
    """Raised when conversation context construction fails."""


class MemoryPolicyError(ConversationMemoryError):
    """Raised when memory policy evaluation fails."""


class DialogueManagerError(ConversationMemoryError):
    """Raised when dialogue manager execution fails."""


# Backward-compatible aliases kept for Phase 1 references.
MemoryStateError = InvalidSessionStateError
MemoryRepositoryError = PostgresRepositoryError
