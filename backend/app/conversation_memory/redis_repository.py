"""Async Redis repository for session-scoped conversation memory."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from redis.exceptions import RedisError

from app.conversation_memory.exceptions import InvalidSessionStateError, RedisRepositoryError, SessionNotFoundError
from app.conversation_memory.models import ConversationTurn, SessionState
from app.conversation_memory.serializers import deserialize_session_state, serialize_session_state, serialize_turn
from app.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class RedisConversationRepository:
    """Handles Redis-backed storage for ``SessionState`` conversation memory."""

    def __init__(self, transient_retries: int = 1) -> None:
        self.transient_retries = max(0, transient_retries)

    @staticmethod
    def _session_key(session_id: str) -> str:
        normalized = session_id.strip()
        if not normalized:
            raise RedisRepositoryError("session_id must be a non-empty string.")
        return f"session:{normalized}"

    @staticmethod
    async def _to_thread(func: Any, *args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(func, *args, **kwargs)

    async def _execute_with_retry(self, operation: str, func: Any, *args: Any, **kwargs: Any) -> Any:
        attempts = self.transient_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                return await self._to_thread(func, *args, **kwargs)
            except RedisError as exc:
                if attempt < attempts:
                    logger.warning(
                        "redis.transient_failure op=%s attempt=%s/%s error=%s",
                        operation,
                        attempt,
                        attempts,
                        type(exc).__name__,
                    )
                    await asyncio.sleep(0.05 * attempt)
                    continue
                logger.exception(
                    "redis.critical_failure op=%s attempts=%s error=%s",
                    operation,
                    attempts,
                    type(exc).__name__,
                )
                raise RedisRepositoryError(f"Redis operation failed: {operation}.") from exc
            except RedisRepositoryError:
                raise
            except Exception as exc:  # pragma: no cover - defensive fallback
                logger.exception("redis.unexpected_failure op=%s", operation)
                raise RedisRepositoryError(f"Unexpected Redis client failure during: {operation}.") from exc

    async def get_session(self, session_id: str) -> SessionState | None:
        """Fetch session memory state from Redis."""
        key = self._session_key(session_id)
        try:
            raw = await self._execute_with_retry(
                "get_session",
                lambda: get_redis_client().get(key),
            )
        except RedisRepositoryError:
            raise

        if not raw:
            return None

        try:
            return deserialize_session_state(raw)
        except InvalidSessionStateError:
            logger.warning("Malformed session payload for key=%s; returning None.", key)
            return None

    async def save_session(self, state: SessionState, ttl_seconds: int = 86_400) -> None:
        """Persist full session state with TTL refresh."""
        key = self._session_key(str(state.session_id))
        payload = serialize_session_state(state)
        try:
            raw = json.dumps(payload, ensure_ascii=False)
            ok = await self._execute_with_retry(
                "save_session",
                lambda: get_redis_client().set(key, raw, ex=ttl_seconds),
            )
            if not ok:
                raise RedisRepositoryError("Redis did not acknowledge save operation.")
        except RedisRepositoryError:
            raise
        except (TypeError, ValueError) as exc:
            logger.exception("Session payload serialization failed for key=%s", key)
            raise RedisRepositoryError("Failed to serialize session payload for Redis.") from exc

        logger.debug("Saved session state key=%s ttl=%s", key, ttl_seconds)

    async def update_session(self, state: SessionState, ttl_seconds: int = 86_400) -> None:
        """Update session state and refresh TTL."""
        await self.save_session(state=state, ttl_seconds=ttl_seconds)

    async def delete_session(self, session_id: str) -> None:
        """Delete session state from Redis if present."""
        key = self._session_key(session_id)
        try:
            await self._execute_with_retry(
                "delete_session",
                lambda: get_redis_client().delete(key),
            )
        except RedisRepositoryError:
            raise

    async def append_turn(
        self,
        session_id: str,
        turn: ConversationTurn,
        ttl_seconds: int = 86_400,
    ) -> SessionState:
        """Append a conversation turn and persist updated state."""
        state = await self.get_session(session_id)
        if state is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        metadata = dict(state.metadata or {})
        raw_turns = metadata.get("turns", [])
        if raw_turns is None:
            raw_turns = []
        if not isinstance(raw_turns, list):
            logger.warning("Invalid turns payload type for session=%s; resetting history.", session_id)
            raw_turns = []

        raw_turns.append(serialize_turn(turn))
        metadata["turns"] = raw_turns

        updated_state = state.model_copy(deep=True)
        updated_state.metadata = metadata
        updated_state.updated_at = datetime.now(timezone.utc)

        await self.update_session(state=updated_state, ttl_seconds=ttl_seconds)
        return updated_state

    async def truncate_history(
        self,
        session_id: str,
        max_turns: int = 10,
        ttl_seconds: int = 86_400,
    ) -> SessionState | None:
        """Trim cached turn history to last ``max_turns`` messages and persist."""
        if max_turns <= 0:
            raise RedisRepositoryError("max_turns must be greater than zero.")

        state = await self.get_session(session_id)
        if state is None:
            return None

        metadata = dict(state.metadata or {})
        raw_turns = metadata.get("turns", [])
        if not isinstance(raw_turns, list):
            logger.warning("Invalid turns payload for session=%s; resetting history.", session_id)
            raw_turns = []

        if len(raw_turns) <= max_turns:
            return state

        metadata["turns"] = raw_turns[-max_turns:]
        updated_state = state.model_copy(deep=True)
        updated_state.metadata = metadata
        updated_state.updated_at = datetime.now(timezone.utc)

        await self.update_session(state=updated_state, ttl_seconds=ttl_seconds)
        return updated_state

    # Backward-compatible adapters for earlier phase placeholders.
    async def get_state(self, session_id: UUID) -> dict[str, Any] | None:
        """Compatibility adapter returning raw state dictionary."""
        state = await self.get_session(str(session_id))
        if state is None:
            return None
        return serialize_session_state(state)

    async def set_state(self, session_id: UUID, state: dict[str, Any]) -> None:
        """Compatibility adapter accepting raw state dictionary."""
        session_state = deserialize_session_state(state)
        if str(session_state.session_id) != str(session_id):
            session_state = session_state.model_copy(update={"session_id": session_id})
        await self.save_session(session_state)
