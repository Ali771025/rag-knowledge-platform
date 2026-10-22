"""Finite state machine for onboarding conversation flow."""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Final

from app.conversation_memory.exceptions import InvalidSessionStateError
from app.conversation_memory.models import ConversationState

logger = logging.getLogger(__name__)

_TRANSITIONS: Final[dict[ConversationState, dict[str, ConversationState]]] = {
    ConversationState.START: {
        "greeting": ConversationState.INTRO,
        "learn_more": ConversationState.INTRO,
        "tell_me_about": ConversationState.INTRO,
    },
    ConversationState.INTRO: {
        "start_learning": ConversationState.EDUCATION,
        "explain": ConversationState.EDUCATION,
    },
    ConversationState.EDUCATION: {
        "ask_question": ConversationState.QNA,
        "clarify": ConversationState.QNA,
        "join": ConversationState.JOIN,
        "participate": ConversationState.JOIN,
    },
    ConversationState.QNA: {
        "join": ConversationState.JOIN,
        "ready": ConversationState.JOIN,
    },
    ConversationState.JOIN: {},
}


def normalize_state(value: str | ConversationState) -> ConversationState:
    """Normalize raw state input into a ``ConversationState`` enum."""
    if isinstance(value, ConversationState):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        try:
            return ConversationState(normalized)
        except ValueError as exc:
            logger.warning("Invalid conversation state value: %s", value)
            raise InvalidSessionStateError(f"Invalid conversation state: {value}") from exc

    logger.warning("Unsupported conversation state type: %s", type(value).__name__)
    raise InvalidSessionStateError(f"Unsupported conversation state type: {type(value).__name__}")


def get_allowed_transitions() -> dict[ConversationState, dict[str, ConversationState]]:
    """Return configured FSM transitions as a read-only copy."""
    return {
        state: dict(MappingProxyType(intent_map))
        for state, intent_map in _TRANSITIONS.items()
    }


def is_valid_transition(
    current_state: ConversationState | str,
    target_state: ConversationState | str,
) -> bool:
    """Check whether transitioning from ``current_state`` to ``target_state`` is allowed."""
    source = normalize_state(current_state)
    target = normalize_state(target_state)
    if source == target:
        return True
    return target in _TRANSITIONS[source].values()


def next_state(current_state: ConversationState | str, intent: str) -> ConversationState:
    """Resolve the next conversation state based on current state and intent."""
    state = normalize_state(current_state)
    normalized_intent = intent.strip().lower()
    if not normalized_intent:
        logger.debug("Empty intent for state=%s; keeping current state.", state.value)
        return state

    target = _TRANSITIONS[state].get(normalized_intent, state)
    logger.debug(
        "FSM transition resolved: current_state=%s intent=%s next_state=%s",
        state.value,
        normalized_intent,
        target.value,
    )
    return target


class ConversationStateMachine:
    """Compatibility wrapper around module-level FSM functions."""

    VALID_STATES: tuple[str, ...] = tuple(state.value for state in ConversationState)

    def normalize_state(self, state: str | ConversationState) -> str:
        """Normalize state and return string value for existing callers."""
        return normalize_state(state).value

    def determine_next_state(self, *, state: str | ConversationState, message: str) -> str:
        """Return next state from a normalized intent string."""
        return next_state(current_state=state, intent=message).value

    def build_actions(self, *, old_state: str | ConversationState, new_state: str | ConversationState) -> list[str]:
        """Build deterministic action tags for state transition tracking."""
        source = normalize_state(old_state)
        target = normalize_state(new_state)
        if source == target:
            return [f"prompt:{target.value}"]
        return [f"transition:{source.value}->{target.value}", f"prompt:{target.value}"]
