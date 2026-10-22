"""Conversation memory package exports with lazy imports to avoid circular startup dependencies."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "ConversationContext",
    "ConversationContextManager",
    "ConversationMemoryDecision",
    "ConversationMemoryService",
    "ConversationSessionManager",
    "ConversationStateMachine",
    "IntentDetector",
    "MemoryPolicy",
    "MemoryTurn",
    "PostgresConversationRepository",
    "RedisConversationRepository",
]


_EXPORTS: dict[str, tuple[str, str]] = {
    "ConversationContext": ("app.conversation_memory.models", "ConversationContext"),
    "ConversationContextManager": ("app.conversation_memory.context_manager", "ConversationContextManager"),
    "ConversationMemoryDecision": ("app.conversation_memory.models", "ConversationMemoryDecision"),
    "ConversationMemoryService": ("app.conversation_memory.service", "ConversationMemoryService"),
    "ConversationSessionManager": ("app.conversation_memory.session_manager", "ConversationSessionManager"),
    "ConversationStateMachine": ("app.conversation_memory.state_machine", "ConversationStateMachine"),
    "IntentDetector": ("app.conversation_memory.intent_detector", "IntentDetector"),
    "MemoryPolicy": ("app.conversation_memory.memory_policy", "MemoryPolicy"),
    "MemoryTurn": ("app.conversation_memory.models", "MemoryTurn"),
    "PostgresConversationRepository": ("app.conversation_memory.postgres_repository", "PostgresConversationRepository"),
    "RedisConversationRepository": ("app.conversation_memory.redis_repository", "RedisConversationRepository"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
