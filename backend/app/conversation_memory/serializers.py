"""Serialization helpers for conversation memory payloads."""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from app.conversation_memory.exceptions import ConversationMemoryError, InvalidSessionStateError
from app.conversation_memory.models import ConversationTurn, SessionState, UserProfile

logger = logging.getLogger(__name__)


def serialize_session_state(state: SessionState) -> dict[str, Any]:
    """Serialize ``SessionState`` to a JSON-safe dict payload."""
    try:
        payload = state.model_dump(mode="json")
    except Exception as exc:  # pragma: no cover - defensive safety net
        logger.exception("Failed to serialize session state.")
        raise InvalidSessionStateError("Failed to serialize session state.") from exc

    logger.debug("Serialized session state for session_id=%s", payload.get("session_id"))
    return payload


def deserialize_session_state(payload: dict[str, Any] | str) -> SessionState:
    """Deserialize payload (dict or JSON string) into ``SessionState``."""
    raw_payload: dict[str, Any]
    if isinstance(payload, str):
        try:
            raw = json.loads(payload)
        except json.JSONDecodeError as exc:
            logger.warning("Invalid JSON string for session state payload.")
            raise InvalidSessionStateError("Invalid session state JSON payload.") from exc

        if not isinstance(raw, dict):
            logger.warning("Session state JSON payload is not an object.")
            raise InvalidSessionStateError("Session state payload must be a JSON object.")
        raw_payload = raw
    elif isinstance(payload, dict):
        raw_payload = payload
    else:
        logger.warning("Unsupported session state payload type: %s", type(payload).__name__)
        raise InvalidSessionStateError("Session state payload must be a dict or JSON string.")

    try:
        session_state = SessionState.model_validate(raw_payload)
    except ValidationError as exc:
        logger.warning("Session state validation failed: %s", exc.errors())
        raise InvalidSessionStateError("Invalid session state payload structure.") from exc

    logger.debug("Deserialized session state for session_id=%s", session_state.session_id)
    return session_state


def serialize_turn(turn: ConversationTurn) -> dict[str, Any]:
    """Serialize ``ConversationTurn`` into a JSON-safe dict."""
    try:
        payload = turn.model_dump(mode="json")
    except Exception as exc:  # pragma: no cover - defensive safety net
        logger.exception("Failed to serialize conversation turn.")
        raise ConversationMemoryError("Failed to serialize conversation turn.") from exc

    logger.debug("Serialized turn for role=%s", payload.get("role"))
    return payload


def serialize_user_profile(profile: UserProfile | None) -> dict[str, Any] | None:
    """Serialize ``UserProfile`` to a JSON-safe dict, preserving ``None``."""
    if profile is None:
        return None

    try:
        payload = profile.model_dump(mode="json")
    except Exception as exc:  # pragma: no cover - defensive safety net
        logger.exception("Failed to serialize user profile.")
        raise ConversationMemoryError("Failed to serialize user profile.") from exc

    logger.debug("Serialized user profile for user_id=%s", payload.get("user_id"))
    return payload


# Backward-compatible aliases kept for Phase 1 references.
def serialize_memory_state(state: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible dict passthrough serializer."""
    return dict(state)


def deserialize_memory_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible dict passthrough deserializer."""
    return dict(payload)
