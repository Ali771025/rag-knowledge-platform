"""PostgreSQL repository for persistent conversation memory data."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.conversation_memory.exceptions import PostgresRepositoryError
from app.conversation_memory.models import ConversationRole, UserProfile
from app.core.database import SessionLocal
from app.models.conversation import Conversation
from app.models.session import Session as UserSession
from app.models.user import User

logger = logging.getLogger(__name__)


def _build_turn_audit_metadata(
    *,
    metadata: dict[str, Any] | None,
    role: str,
    session_id: UUID,
    user_id: UUID | None,
) -> dict[str, Any]:
    """Build trace-friendly metadata that is safe to log for DB auditing."""
    base = dict(metadata or {})
    base.setdefault("role", role)
    base.setdefault("session_id", str(session_id))
    if user_id is not None:
        base.setdefault("user_id", str(user_id))
    return base


class PostgresConversationRepository:
    """Provides async-style persistence methods backed by synchronous SQLAlchemy."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal

    @staticmethod
    def _coerce_uuid(value: UUID | str, field_name: str) -> UUID:
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise PostgresRepositoryError(f"Invalid UUID for {field_name}.") from exc

    @staticmethod
    async def _to_thread(func: Any, *args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(func, *args, **kwargs)

    @staticmethod
    def _is_transient_error(exc: SQLAlchemyError) -> bool:
        # Best-effort classification for operational/network-style DB failures.
        text = str(exc).lower()
        transient_markers = (
            "timeout",
            "timed out",
            "connection reset",
            "could not connect",
            "connection refused",
            "server closed the connection",
            "operationalerror",
        )
        return any(marker in text for marker in transient_markers)

    async def save_conversation_turn(
        self,
        session_id: UUID | str,
        user_id: UUID | str | None,
        role: str,
        message: str,
        timestamp: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Persist a conversation turn record."""
        session_uuid = self._coerce_uuid(session_id, "session_id")
        user_uuid = self._coerce_uuid(user_id, "user_id") if user_id else None

        # TODO: Conversation ORM currently has no metadata column. Persisting metadata
        # requires a schema migration or side table in a future phase.
        audit_meta = _build_turn_audit_metadata(
            metadata=metadata,
            role=role,
            session_id=session_uuid,
            user_id=user_uuid,
        )
        if metadata:
            logger.debug(
                "db.turn_metadata_not_persisted session_id=%s role=%s keys=%s",
                session_uuid,
                role,
                sorted(audit_meta.keys()),
            )

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        def _op(persist_user_uuid: UUID | None) -> bool:
            db: Session = self._session_factory()
            try:
                session_record = db.get(UserSession, session_uuid)
                if session_record is None:
                    logger.info("db.skip_turn_logging_missing_session session_id=%s", session_uuid)
                    return False
                record = Conversation(
                    session_id=session_uuid,
                    user_id=persist_user_uuid,
                    role=role,
                    message=message,
                    created_at=timestamp,
                )
                db.add(record)
                db.commit()
                return True
            except SQLAlchemyError:
                db.rollback()
                raise
            finally:
                db.close()

        try:
            saved = await self._to_thread(_op, user_uuid)
            if not saved:
                return
            logger.debug(
                "Saved conversation turn session_id=%s role=%s audit_keys=%s",
                session_uuid,
                role,
                sorted(audit_meta.keys()),
            )
        except IntegrityError as exc:
            text = str(exc).lower()
            is_user_fk_violation = "user" in text and "foreign key" in text
            is_session_fk_violation = "session" in text and "foreign key" in text

            if is_user_fk_violation and user_uuid is not None:
                logger.warning(
                    "db.turn_logging_retry_without_user session_id=%s user_id=%s",
                    session_uuid,
                    user_uuid,
                )
                try:
                    saved = await self._to_thread(_op, None)
                    if saved:
                        logger.debug(
                            "Saved conversation turn without user relation session_id=%s role=%s",
                            session_uuid,
                            role,
                        )
                    return
                except SQLAlchemyError as retry_exc:
                    if "session" in str(retry_exc).lower() and "foreign key" in str(retry_exc).lower():
                        logger.warning("db.skip_turn_logging_missing_session session_id=%s", session_uuid)
                        return
                    raise PostgresRepositoryError("Failed to save conversation turn.") from retry_exc

            if is_session_fk_violation:
                logger.warning("db.skip_turn_logging_missing_session session_id=%s", session_uuid)
                return

            level = logger.warning if self._is_transient_error(exc) else logger.exception
            level(
                "db.%s save_conversation_turn session_id=%s error=%s",
                "transient_failure" if self._is_transient_error(exc) else "critical_failure",
                session_uuid,
                type(exc).__name__,
            )
            raise PostgresRepositoryError("Failed to save conversation turn.") from exc
        except SQLAlchemyError as exc:
            level = logger.warning if self._is_transient_error(exc) else logger.exception
            level(
                "db.%s save_conversation_turn session_id=%s error=%s",
                "transient_failure" if self._is_transient_error(exc) else "critical_failure",
                session_uuid,
                type(exc).__name__,
            )
            raise PostgresRepositoryError("Failed to save conversation turn.") from exc

    async def save_session_metadata(
        self,
        session_id: UUID | str,
        user_id: UUID | str | None,
        metadata: dict[str, Any],
    ) -> None:
        """Merge and persist session-scoped metadata in the session state JSON."""
        session_uuid = self._coerce_uuid(session_id, "session_id")
        user_uuid = self._coerce_uuid(user_id, "user_id") if user_id else None

        def _op() -> bool:
            db: Session = self._session_factory()
            try:
                session_record = db.get(UserSession, session_uuid)
                if session_record is None:
                    logger.info("db.skip_session_metadata_missing_session session_id=%s", session_uuid)
                    return False
                if user_uuid is not None and session_record.user_id != user_uuid:
                    logger.warning(
                        "db.skip_session_metadata_user_mismatch session_id=%s session_user_id=%s provided_user_id=%s",
                        session_uuid,
                        session_record.user_id,
                        user_uuid,
                    )
                    return False

                current_state = dict(session_record.state or {})
                existing_meta = current_state.get("metadata")
                if not isinstance(existing_meta, dict):
                    existing_meta = {}
                merged_meta = {**existing_meta, **dict(metadata)}
                current_state["metadata"] = merged_meta
                session_record.state = current_state
                db.add(session_record)
                db.commit()
                return True
            except SQLAlchemyError:
                db.rollback()
                raise
            finally:
                db.close()

        try:
            saved = await self._to_thread(_op)
            if not saved:
                return
            logger.debug("Saved session metadata session_id=%s keys=%s", session_uuid, sorted(metadata.keys()))
        except SQLAlchemyError as exc:
            level = logger.warning if self._is_transient_error(exc) else logger.exception
            level(
                "db.%s save_session_metadata session_id=%s error=%s",
                "transient_failure" if self._is_transient_error(exc) else "critical_failure",
                session_uuid,
                type(exc).__name__,
            )
            raise PostgresRepositoryError("Failed to save session metadata.") from exc

    async def get_user_profile(self, user_id: UUID | str) -> UserProfile | None:
        """Return a normalized user profile if the user exists."""
        user_uuid = self._coerce_uuid(user_id, "user_id")

        def _op() -> User | None:
            db: Session = self._session_factory()
            try:
                return db.get(User, user_uuid)
            finally:
                db.close()

        try:
            user = await self._to_thread(_op)
        except ProgrammingError as exc:
            logger.warning(
                "db.skip_user_profile_schema_mismatch user_id=%s error=%s",
                user_uuid,
                type(exc).__name__,
            )
            return None
        except SQLAlchemyError as exc:
            level = logger.warning if self._is_transient_error(exc) else logger.exception
            level(
                "db.%s get_user_profile user_id=%s error=%s",
                "transient_failure" if self._is_transient_error(exc) else "critical_failure",
                user_uuid,
                type(exc).__name__,
            )
            raise PostgresRepositoryError("Failed to load user profile.") from exc

        if user is None:
            return None

        first_name: str | None = None
        last_name: str | None = None
        if user.full_name:
            parts = user.full_name.strip().split(maxsplit=1)
            first_name = parts[0] if parts else None
            last_name = parts[1] if len(parts) > 1 else None

        return UserProfile(
            user_id=user.id,
            first_name=first_name,
            last_name=last_name,
            email=user.email,
        )

    async def upsert_user_profile(self, profile: UserProfile) -> UserProfile:
        """
        Update user profile fields for an existing user record.

        Note: creating new users is intentionally not performed here because the
        existing schema requires authentication fields (e.g. hashed_password).
        """
        if profile.user_id is None:
            raise PostgresRepositoryError("UserProfile.user_id is required for upsert.")

        user_uuid = self._coerce_uuid(profile.user_id, "user_id")

        def _op() -> User:
            db: Session = self._session_factory()
            try:
                user = db.get(User, user_uuid)
                if user is None:
                    raise PostgresRepositoryError(
                        "Cannot upsert non-existent user without auth fields; create user in user service first."
                    )

                if profile.email is not None:
                    user.email = profile.email

                full_name_parts = [part for part in [profile.first_name, profile.last_name] if part]
                if full_name_parts:
                    user.full_name = " ".join(full_name_parts)

                db.add(user)
                db.commit()
                db.refresh(user)
                return user
            finally:
                db.close()

        try:
            user = await self._to_thread(_op)
        except PostgresRepositoryError:
            raise
        except SQLAlchemyError as exc:
            level = logger.warning if self._is_transient_error(exc) else logger.exception
            level(
                "db.%s upsert_user_profile user_id=%s error=%s",
                "transient_failure" if self._is_transient_error(exc) else "critical_failure",
                user_uuid,
                type(exc).__name__,
            )
            raise PostgresRepositoryError("Failed to upsert user profile.") from exc

        first_name: str | None = None
        last_name: str | None = None
        if user.full_name:
            parts = user.full_name.strip().split(maxsplit=1)
            first_name = parts[0] if parts else None
            last_name = parts[1] if len(parts) > 1 else None

        return UserProfile(
            user_id=user.id,
            first_name=first_name,
            last_name=last_name,
            email=user.email,
            preferences=profile.preferences,
            attributes=profile.attributes,
        )

    async def get_session_logs(self, session_id: UUID | str, limit: int = 100) -> list[dict[str, Any]]:
        """Return ordered conversation logs for a session."""
        session_uuid = self._coerce_uuid(session_id, "session_id")
        safe_limit = max(1, min(int(limit), 1000))

        def _op() -> list[Conversation]:
            db: Session = self._session_factory()
            try:
                stmt = (
                    select(Conversation)
                    .where(Conversation.session_id == session_uuid)
                    .order_by(Conversation.created_at.asc())
                    .limit(safe_limit)
                )
                return list(db.scalars(stmt).all())
            finally:
                db.close()

        try:
            rows = await self._to_thread(_op)
        except SQLAlchemyError as exc:
            level = logger.warning if self._is_transient_error(exc) else logger.exception
            level(
                "db.%s get_session_logs session_id=%s error=%s",
                "transient_failure" if self._is_transient_error(exc) else "critical_failure",
                session_uuid,
                type(exc).__name__,
            )
            raise PostgresRepositoryError("Failed to load session logs.") from exc

        logs: list[dict[str, Any]] = []
        for row in rows:
            role_value = row.role
            if role_value not in {r.value for r in ConversationRole}:
                role_value = ConversationRole.SYSTEM.value
            logs.append(
                {
                    "id": str(row.id),
                    "session_id": str(row.session_id),
                    "user_id": str(row.user_id) if row.user_id else None,
                    "role": role_value,
                    "message": row.message,
                    "timestamp": row.created_at.isoformat() if row.created_at else None,
                    "metadata": None,  # TODO: add when conversation metadata column/table exists.
                }
            )
        return logs
