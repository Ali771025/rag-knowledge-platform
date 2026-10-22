"""Redis-backed ephemeral repository for persona transition helper state."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Protocol

from redis.exceptions import RedisError

from app.core.redis_client import get_redis_client
from app.internal.persona.transition_buffer_models import (
    PersonaTransitionBuffer,
    PersonaTransitionEvaluation,
    TransitionCandidate,
)
from app.internal.persona.transition_buffer_serializers import (
    TransitionBufferSerializationError,
    deserialize_transition_buffer,
    serialize_transition_buffer,
)


class PersonaTransitionBufferRepositoryError(RuntimeError):
    """Raised for typed repository failures while interacting with Redis."""


class PersonaTransitionBufferStore(Protocol):
    """Interface for transition-buffer stores used by transition manager."""

    async def get_buffer(self, session_id: str) -> PersonaTransitionBuffer | None:
        """Fetch current transition buffer for a session."""

    async def append_evaluation(self, session_id: str, evaluation: PersonaTransitionEvaluation) -> PersonaTransitionBuffer:
        """Append evaluation snapshot and retain only recent rolling window."""

    async def set_transition_candidate(self, session_id: str, candidate: TransitionCandidate) -> PersonaTransitionBuffer:
        """Store the latest transition candidate in the buffer."""

    async def clear_transition_candidate(self, session_id: str) -> PersonaTransitionBuffer | None:
        """Remove transition candidate and return updated buffer when present."""

    async def delete_buffer(self, session_id: str) -> None:
        """Delete transition buffer key from Redis."""


class RedisPersonaTransitionBufferRepository(PersonaTransitionBufferStore):
    """Redis implementation for ephemeral persona transition state."""

    def __init__(self, ttl_seconds: int = 1800, max_items: int = 3, transient_retries: int = 1) -> None:
        if ttl_seconds <= 0:
            raise PersonaTransitionBufferRepositoryError("ttl_seconds must be greater than zero.")
        if max_items <= 0:
            raise PersonaTransitionBufferRepositoryError("max_items must be greater than zero.")

        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self.transient_retries = max(0, transient_retries)

    @staticmethod
    def key_for_session(session_id: str) -> str:
        normalized = session_id.strip()
        if not normalized:
            raise PersonaTransitionBufferRepositoryError("session_id must be a non-empty string.")
        return f"persona_transition_buffer:{normalized}"

    @staticmethod
    async def _to_thread(func: Any, *args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(func, *args, **kwargs)

    async def _execute(self, operation: str, func: Any, *args: Any, **kwargs: Any) -> Any:
        attempts = self.transient_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                return await self._to_thread(func, *args, **kwargs)
            except RedisError as exc:
                if attempt < attempts:
                    await asyncio.sleep(0.05 * attempt)
                    continue
                raise PersonaTransitionBufferRepositoryError(f"Redis operation failed: {operation}") from exc
            except PersonaTransitionBufferRepositoryError:
                raise
            except Exception as exc:  # pragma: no cover - defensive catch
                raise PersonaTransitionBufferRepositoryError(f"Unexpected failure during operation: {operation}") from exc

    async def get_buffer(self, session_id: str) -> PersonaTransitionBuffer | None:
        key = self.key_for_session(session_id)
        raw = await self._execute("get_buffer", lambda: get_redis_client().get(key))
        if not raw:
            return None

        try:
            return deserialize_transition_buffer(raw)
        except TransitionBufferSerializationError:
            return None

    async def save_buffer(self, buffer: PersonaTransitionBuffer) -> None:
        key = self.key_for_session(buffer.session_id)
        try:
            payload = serialize_transition_buffer(buffer)
        except TransitionBufferSerializationError as exc:
            raise PersonaTransitionBufferRepositoryError("Failed to serialize transition buffer.") from exc
        ok = await self._execute(
            "save_buffer",
            lambda: get_redis_client().set(key, payload, ex=self.ttl_seconds),
        )
        if not ok:
            raise PersonaTransitionBufferRepositoryError("Redis did not acknowledge transition buffer write.")

    async def append_evaluation(self, session_id: str, evaluation: PersonaTransitionEvaluation) -> PersonaTransitionBuffer:
        buffer = await self.get_buffer(session_id)
        if buffer is None:
            evaluations = [evaluation]
        else:
            evaluations = [*buffer.evaluations, evaluation]

        recent_evaluations = evaluations[-self.max_items :]
        recent_confidence = [item.confidence for item in recent_evaluations]

        transition_candidate = buffer.transition_candidate if buffer is not None else None
        updated = PersonaTransitionBuffer(
            session_id=session_id,
            evaluations=recent_evaluations,
            rolling_confidence=recent_confidence,
            transition_candidate=transition_candidate,
            updated_at=datetime.now(timezone.utc),
        )
        await self.save_buffer(updated)
        return updated

    async def set_transition_candidate(self, session_id: str, candidate: TransitionCandidate) -> PersonaTransitionBuffer:
        buffer = await self.get_buffer(session_id)
        if buffer is None:
            updated = PersonaTransitionBuffer(
                session_id=session_id,
                evaluations=[],
                rolling_confidence=[],
                transition_candidate=candidate,
                updated_at=datetime.now(timezone.utc),
            )
        else:
            updated = buffer.model_copy(
                update={
                    "transition_candidate": candidate,
                    "updated_at": datetime.now(timezone.utc),
                }
            )

        await self.save_buffer(updated)
        return updated

    async def clear_transition_candidate(self, session_id: str) -> PersonaTransitionBuffer | None:
        buffer = await self.get_buffer(session_id)
        if buffer is None:
            return None

        updated = buffer.model_copy(
            update={
                "transition_candidate": None,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        await self.save_buffer(updated)
        return updated

    async def delete_buffer(self, session_id: str) -> None:
        key = self.key_for_session(session_id)
        await self._execute("delete_buffer", lambda: get_redis_client().delete(key))
