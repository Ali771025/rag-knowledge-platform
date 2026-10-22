"""Session manager for conversation memory lifecycle operations."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, TypeVar
from uuid import UUID, uuid4

from app.conversation_memory.exceptions import InvalidSessionStateError, RedisRepositoryError, SessionNotFoundError
from app.conversation_memory.memory_policy import MemoryPolicy
from app.conversation_memory.models import ConversationRole, ConversationState, ConversationTurn, SessionState, UserProfile
from app.conversation_memory.redis_repository import RedisConversationRepository
from app.conversation_memory.serializers import deserialize_session_state, serialize_session_state, serialize_user_profile
from app.conversation_memory.state_machine import normalize_state
from app.entry import EntryContextInput, EntryContextParser

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ConversationSessionManager:
    """Coordinates creation, loading, updates, and retention for session memory."""

    def __init__(
        self,
        redis_repository: RedisConversationRepository | None = None,
        memory_policy: MemoryPolicy | None = None,
        entry_context_parser: EntryContextParser | None = None,
        default_ttl_seconds: int = 86_400,
        max_turns: int = 10,
    ) -> None:
        self.redis_repository = redis_repository or RedisConversationRepository()
        self.memory_policy = memory_policy or MemoryPolicy()
        self.entry_context_parser = entry_context_parser or EntryContextParser()
        self.default_ttl_seconds = default_ttl_seconds
        self.max_turns = max_turns

    def create_session(
        self,
        user_id: str,
        user_profile: UserProfile | None = None,
        bootstrap_input: dict[str, Any] | None = None,
    ) -> SessionState:
        """Create and persist a new session in START state."""
        safe_user_id = str(user_id).strip()
        if not safe_user_id:
            raise InvalidSessionStateError("user_id is required to create a session.")

        now = datetime.now(timezone.utc)
        session_id = uuid4()
        metadata: dict[str, Any] = {
            "user_id": safe_user_id,
            "turns": [],
        }
        serialized_profile = serialize_user_profile(user_profile)
        if serialized_profile is not None:
            metadata["user_profile"] = serialized_profile
        metadata["entry_context"] = self._build_entry_context(
            session_id=str(session_id),
            bootstrap_input=bootstrap_input or {},
        )

        state = SessionState(
            session_id=session_id,
            state=ConversationState.START,
            created_at=now,
            updated_at=now,
            metadata=metadata,
        )
        try:
            self._run_coro(self.redis_repository.save_session(state, ttl_seconds=self.default_ttl_seconds))
        except RedisRepositoryError as exc:
            logger.error("session.create.critical_redis_failure session_id=%s", session_id)
            raise
        logger.info("Created conversation session session_id=%s user_id=%s", session_id, safe_user_id)
        return state

    def create_anonymous_session(
        self,
        *,
        bootstrap_input: dict[str, Any] | None = None,
    ) -> SessionState:
        """Create and persist a new anonymous session in START state."""
        now = datetime.now(timezone.utc)
        session_id = uuid4()
        metadata: dict[str, Any] = {
            "turns": [],
        }
        metadata["entry_context"] = self._build_entry_context(
            session_id=str(session_id),
            bootstrap_input=bootstrap_input or {},
        )

        state = SessionState(
            session_id=session_id,
            state=ConversationState.START,
            created_at=now,
            updated_at=now,
            metadata=metadata,
        )
        try:
            self._run_coro(self.redis_repository.save_session(state, ttl_seconds=self.default_ttl_seconds))
        except RedisRepositoryError:
            logger.error("session.create_anonymous.critical_redis_failure session_id=%s", session_id)
            raise
        logger.info("Created anonymous conversation session session_id=%s", session_id)
        return state

    def load_session(self, session_id: str) -> SessionState:
        """Load an existing session or raise ``SessionNotFoundError``."""
        safe_session_id = self._safe_session_id(session_id)
        state = self._run_coro(self.redis_repository.get_session(safe_session_id))
        if state is None:
            raise SessionNotFoundError(f"Session not found: {safe_session_id}")
        return state

    def get_or_create_session(
        self,
        session_id: str | None,
        user_id: str | None,
        bootstrap_input: dict[str, Any] | None = None,
    ) -> SessionState:
        """Load by session id when possible; otherwise create from user id."""
        if session_id and str(session_id).strip():
            try:
                return self.load_session(session_id)
            except SessionNotFoundError:
                logger.info("Session not found for id=%s; fallback to create if user_id provided.", session_id)

        if user_id and str(user_id).strip():
            return self.create_session(user_id=str(user_id), bootstrap_input=bootstrap_input)

        return self.create_anonymous_session(bootstrap_input=bootstrap_input)

    def update_state(self, session_id: str, new_state: ConversationState | str) -> SessionState:
        """Update and persist conversation state."""
        state = self.load_session(session_id)
        normalized_state = normalize_state(new_state)

        updated = state.model_copy(
            update={
                "state": normalized_state,
                "updated_at": datetime.now(timezone.utc),
            },
            deep=True,
        )
        try:
            self._run_coro(self.redis_repository.update_session(updated, ttl_seconds=self.default_ttl_seconds))
        except RedisRepositoryError:
            logger.error("session.update_state.critical_redis_failure session_id=%s", updated.session_id)
            raise
        logger.debug("Updated session state session_id=%s state=%s", updated.session_id, updated.state.value)
        return updated

    def append_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        intent: str | None = None,
        metadata: dict | None = None,
    ) -> SessionState:
        """Append a turn, apply memory policy, and persist updated session."""
        safe_session_id = self._safe_session_id(session_id)
        safe_content = content.strip()
        if not safe_content:
            raise InvalidSessionStateError("content cannot be empty.")

        conversation_role = self._normalize_role(role)
        turn_metadata: dict[str, Any] = dict(metadata or {})
        if intent is not None:
            turn_metadata["intent"] = intent

        turn = ConversationTurn(
            role=conversation_role,
            message=safe_content,
            timestamp=datetime.now(timezone.utc),
            metadata=turn_metadata,
        )
        try:
            appended_state = self._run_coro(
                self.redis_repository.append_turn(
                    session_id=safe_session_id,
                    turn=turn,
                    ttl_seconds=self.default_ttl_seconds,
                )
            )
        except RedisRepositoryError:
            logger.error("session.append_turn.critical_redis_failure session_id=%s", safe_session_id)
            raise

        policy_applied = self.memory_policy.apply_memory_policy(
            session_state=appended_state,
            max_turns=self.max_turns,
        )
        policy_applied.updated_at = datetime.now(timezone.utc)
        try:
            self._run_coro(
                self.redis_repository.update_session(policy_applied, ttl_seconds=self.default_ttl_seconds)
            )
        except RedisRepositoryError:
            logger.error("session.append_turn.policy_persist_critical_failure session_id=%s", safe_session_id)
            raise
        logger.debug(
            "Appended turn and applied policy session_id=%s role=%s",
            safe_session_id,
            conversation_role.value,
        )
        return policy_applied

    def delete_session(self, session_id: str) -> None:
        """Delete session from Redis memory store."""
        safe_session_id = self._safe_session_id(session_id)
        try:
            self._run_coro(self.redis_repository.delete_session(safe_session_id))
        except RedisRepositoryError:
            logger.error("session.delete.critical_redis_failure session_id=%s", safe_session_id)
            raise
        logger.info("Deleted session session_id=%s", safe_session_id)

    def get_context_friendly_state(self, session_id: str) -> SessionState:
        """Return session state normalized for context building."""
        state = self.load_session(session_id)
        metadata = dict(state.metadata or {})
        turns = metadata.get("turns", [])
        if isinstance(turns, list) and len(turns) > self.max_turns:
            metadata["turns"] = turns[-self.max_turns :]
            state = state.model_copy(update={"metadata": metadata}, deep=True)
        return state

    # Backward-compatible adapters for existing Phase 1 service calls.
    def get_state(self, session_id: UUID) -> dict[str, Any] | None:
        """Return serialized state dict or ``None`` when session is missing."""
        try:
            state = self.load_session(str(session_id))
        except SessionNotFoundError:
            return None
        return serialize_session_state(state)

    def update_session_state(self, session_id: UUID, state: dict[str, Any]) -> dict[str, Any] | None:
        """Compatibility updater that accepts raw state payload."""
        try:
            current = self.load_session(str(session_id))
        except SessionNotFoundError:
            return None

        incoming = deserialize_session_state(
            {
                "session_id": str(session_id),
                "state": state.get("state", current.state.value),
                "created_at": current.created_at.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "metadata": dict(state.get("metadata", current.metadata)),
            }
        )
        try:
            self._run_coro(self.redis_repository.update_session(incoming, ttl_seconds=self.default_ttl_seconds))
        except RedisRepositoryError:
            logger.error("session.update_session_state.critical_redis_failure session_id=%s", session_id)
            raise
        return serialize_session_state(incoming)

    def _build_entry_context(self, *, session_id: str, bootstrap_input: dict[str, Any]) -> dict[str, Any]:
        payload = dict(bootstrap_input)
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        parsed = self.entry_context_parser.parse(
            EntryContextInput(
                session_id=session_id,
                message=str(payload.get("message", "")),
                referrer_id=payload.get("referrer_id"),
                referral_link_type=payload.get("referral_link_type"),
                network_position=payload.get("network_position"),
                device_info=payload.get("device_info") if isinstance(payload.get("device_info"), dict) else {},
                language_hint=payload.get("language_hint"),
                time_of_day=payload.get("time_of_day"),
                campaign_source=payload.get("campaign_source"),
                medium=payload.get("medium"),
                pre_engagement=payload.get("pre_engagement"),
                metadata=metadata,
            )
        )
        return parsed.model_dump(mode="json")

    def _safe_session_id(self, session_id: str) -> str:
        value = str(session_id).strip()
        if not value:
            raise InvalidSessionStateError("session_id must be a non-empty string.")
        return value

    @staticmethod
    def _normalize_role(role: str) -> ConversationRole:
        try:
            return ConversationRole(role.strip().lower())
        except ValueError as exc:
            raise InvalidSessionStateError(f"Unsupported conversation role: {role}") from exc

    @staticmethod
    def _run_coro(coro: Any) -> T:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError(
            "ConversationSessionManager synchronous methods cannot be called from an active event loop."
        )
