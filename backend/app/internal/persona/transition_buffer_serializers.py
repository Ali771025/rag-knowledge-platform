"""Serialization helpers for persona transition Redis payloads."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.internal.persona.transition_buffer_models import PersonaTransitionBuffer


class TransitionBufferSerializationError(ValueError):
    """Raised when transition buffer payloads cannot be encoded or decoded."""


def serialize_transition_buffer(buffer: PersonaTransitionBuffer) -> str:
    """Serialize transition buffer model to compact JSON for Redis storage."""

    try:
        return json.dumps(buffer.model_dump(mode="json"), separators=(",", ":"), ensure_ascii=True)
    except (TypeError, ValueError) as exc:
        raise TransitionBufferSerializationError("Failed to serialize transition buffer payload.") from exc


def deserialize_transition_buffer(payload: str | dict[str, Any]) -> PersonaTransitionBuffer:
    """Deserialize Redis payload into typed transition buffer model."""

    try:
        data = json.loads(payload) if isinstance(payload, str) else payload
    except (TypeError, ValueError) as exc:
        raise TransitionBufferSerializationError("Transition buffer payload is not valid JSON.") from exc

    try:
        return PersonaTransitionBuffer.model_validate(data)
    except ValidationError as exc:
        raise TransitionBufferSerializationError("Transition buffer payload did not match schema.") from exc
