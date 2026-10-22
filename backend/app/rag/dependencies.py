"""Dependency providers for RAG API integration."""

from __future__ import annotations

import logging

from app.conversation_memory.context_manager import ConversationContextManager
from app.conversation_memory.exceptions import ConversationMemoryError
from app.conversation_memory.models import ConversationContext
from app.conversation_memory.session_manager import ConversationSessionManager
from app.rag.rag_orchestrator import RAGOrchestrator, RAGPolicyConfig

logger = logging.getLogger(__name__)


def get_rag_policy_config() -> RAGPolicyConfig:
    """Return default RAG policy config."""
    return RAGPolicyConfig()


def get_rag_orchestrator() -> RAGOrchestrator:
    """Return orchestrator instance for request handling."""
    return RAGOrchestrator(policy=get_rag_policy_config())


def get_session_manager() -> ConversationSessionManager:
    """Return conversation session manager dependency."""
    return ConversationSessionManager()


def get_context_manager() -> ConversationContextManager:
    """Return conversation context manager dependency."""
    return ConversationContextManager()


def resolve_conversation_context(
    *,
    session_id: str | None,
    user_query: str,
    session_manager: ConversationSessionManager | None = None,
    context_manager: ConversationContextManager | None = None,
) -> ConversationContext | None:
    """Load conversation context from conversation layer without session business logic."""
    if not session_id:
        return None

    manager = session_manager or get_session_manager()
    context_builder = context_manager or get_context_manager()

    try:
        session_state = manager.get_context_friendly_state(session_id=session_id)
        return context_builder.build_from_session_state(
            session_state=session_state,
            new_user_message=user_query,
            max_turns=10,
        )
    except ConversationMemoryError as exc:
        logger.warning(
            "rag_context_resolution_failed session_id=%s error=%s",
            session_id,
            type(exc).__name__,
        )
        return None
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("rag_context_resolution_unexpected_error", exc_info=exc)
        return None
