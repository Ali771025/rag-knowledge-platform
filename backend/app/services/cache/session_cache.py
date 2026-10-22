"""Redis-backed session context cache for conversational state."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.models.cache.contracts import CacheInvalidateResult, SessionContextPayload
from app.services.cache.redis_client import AsyncRedisClient, RedisOperationError, RedisSerializationError


class SessionContextUpdate(BaseModel):
    """Typed partial update payload for session context merges."""

    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    recent_messages: list[dict[str, Any]] | None = None
    dialogue_state: str | None = Field(default=None, min_length=1, max_length=128)
    onboarding_step: str | None = Field(default=None, min_length=1, max_length=128)
    user_profile_snapshot: dict[str, Any] | None = None
    attributes: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SessionCache:
    """Session cache with explicit TTL and merge/overwrite update behavior."""

    def __init__(
        self,
        redis_client: AsyncRedisClient,
        default_ttl_seconds: int = 3600,
        min_ttl_seconds: int = 1,
        max_ttl_seconds: int = 7 * 24 * 3600,
    ) -> None:
        self.redis_client = redis_client
        self.default_ttl_seconds = default_ttl_seconds
        self.min_ttl_seconds = min_ttl_seconds
        self.max_ttl_seconds = max_ttl_seconds

    async def get_session_context(
        self,
        session_id: str,
        namespace: str = "session",
        max_age_seconds: int | None = None,
    ) -> SessionContextPayload | None:
        """Fetch and validate one session context document from Redis."""
        redis_key = self._build_session_key(session_id=session_id, namespace=namespace)
        try:
            payload = await self.redis_client.get_json(redis_key)
        except (RedisOperationError, RedisSerializationError):
            return None

        if payload is None:
            return None

        try:
            context = SessionContextPayload.model_validate(payload)
        except ValidationError:
            return None

        if not self._is_fresh(context=context, max_age_seconds=max_age_seconds):
            return None
        return context

    async def update_session_context(
        self,
        session_id: str,
        updates: SessionContextUpdate | SessionContextPayload | dict[str, Any],
        namespace: str = "session",
        ttl_seconds: int | None = None,
        overwrite: bool = False,
    ) -> SessionContextPayload:
        """Update session state using merge (default) or full overwrite strategy."""
        ttl = self._resolve_ttl(ttl_seconds)
        current = await self.get_session_context(session_id=session_id, namespace=namespace)
        normalized_update = self._to_update_payload(updates)

        now = datetime.now(timezone.utc)
        if overwrite or current is None:
            merged = SessionContextPayload(
                session_id=session_id,
                user_id=normalized_update.user_id,
                recent_messages=normalized_update.recent_messages or [],
                dialogue_state=normalized_update.dialogue_state,
                onboarding_step=normalized_update.onboarding_step,
                user_profile_snapshot=normalized_update.user_profile_snapshot or {},
                attributes=normalized_update.attributes or {},
                last_updated_at=now,
            )
        else:
            merged = self._merge_context(current=current, updates=normalized_update, now=now)

        redis_key = self._build_session_key(session_id=session_id, namespace=namespace)
        await self.redis_client.set_json(redis_key, merged.model_dump(mode="json"), ttl_seconds=ttl)
        return merged

    async def clear_session_context(
        self,
        session_id: str,
        namespace: str = "session",
    ) -> CacheInvalidateResult:
        """Clear session context for a specific session ID."""
        redis_key = self._build_session_key(session_id=session_id, namespace=namespace)
        deleted = await self.redis_client.delete(redis_key)
        return CacheInvalidateResult(
            success=deleted > 0,
            namespace=namespace,
            cache_key=session_id,
            invalidated_count=deleted,
            message="session_context_cleared",
        )

    async def get_context(self, session_id: str) -> SessionContextPayload | None:
        """Backward-compatible alias for session context retrieval."""
        return await self.get_session_context(session_id=session_id)

    async def set_context(self, payload: SessionContextPayload) -> bool:
        """Backward-compatible alias for full session context write."""
        await self.update_session_context(
            session_id=payload.session_id,
            updates=payload,
            ttl_seconds=None,
            overwrite=True,
        )
        return True

    def _resolve_ttl(self, requested_ttl: int | None) -> int:
        ttl = self.default_ttl_seconds if requested_ttl is None else requested_ttl
        if ttl < self.min_ttl_seconds or ttl > self.max_ttl_seconds:
            raise ValueError(
                f"ttl_seconds must be between {self.min_ttl_seconds} and {self.max_ttl_seconds}, got {ttl}."
            )
        return ttl

    def _build_session_key(self, session_id: str, namespace: str) -> str:
        return self.redis_client.build_key(namespace, "context", session_id)

    @staticmethod
    def _to_update_payload(updates: SessionContextUpdate | SessionContextPayload | dict[str, Any]) -> SessionContextUpdate:
        if isinstance(updates, SessionContextUpdate):
            return updates
        if isinstance(updates, dict):
            return SessionContextUpdate.model_validate(updates)
        return SessionContextUpdate(
            user_id=updates.user_id,
            recent_messages=updates.recent_messages,
            dialogue_state=updates.dialogue_state,
            onboarding_step=updates.onboarding_step,
            user_profile_snapshot=updates.user_profile_snapshot,
            attributes=updates.attributes,
        )

    @staticmethod
    def _merge_context(
        current: SessionContextPayload,
        updates: SessionContextUpdate,
        now: datetime,
    ) -> SessionContextPayload:
        current_data = current.model_dump()

        if updates.user_id is not None:
            current_data["user_id"] = updates.user_id
        if updates.recent_messages is not None:
            current_data["recent_messages"] = updates.recent_messages
        if updates.dialogue_state is not None:
            current_data["dialogue_state"] = updates.dialogue_state
        if updates.onboarding_step is not None:
            current_data["onboarding_step"] = updates.onboarding_step
        if updates.user_profile_snapshot is not None:
            merged_profile = dict(current.user_profile_snapshot)
            merged_profile.update(updates.user_profile_snapshot)
            current_data["user_profile_snapshot"] = merged_profile
        if updates.attributes is not None:
            merged_attributes = dict(current.attributes)
            merged_attributes.update(updates.attributes)
            current_data["attributes"] = merged_attributes

        current_data["last_updated_at"] = now
        return SessionContextPayload.model_validate(current_data)

    @staticmethod
    def _is_fresh(context: SessionContextPayload, max_age_seconds: int | None) -> bool:
        if max_age_seconds is None:
            return True
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
        return context.last_updated_at >= cutoff
