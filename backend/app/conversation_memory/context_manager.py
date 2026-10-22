"""Context management for conversation memory."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.conversation_memory.exceptions import ContextBuildError
from app.conversation_memory.models import ConversationContext, ConversationState, ConversationTurn, SessionState, UserProfile

logger = logging.getLogger(__name__)


def build_context(session_state: SessionState, new_user_message: str, max_turns: int = 10) -> ConversationContext:
    """
    Build a structured conversation context for RAG/response generation.

    Includes current state, last N turns, user profile, latest user message,
    memory summary, and metadata snapshot.
    """
    if max_turns <= 0:
        raise ContextBuildError("max_turns must be greater than zero.")

    if not isinstance(new_user_message, str):
        raise ContextBuildError("new_user_message must be a string.")

    try:
        validated_state = _validate_session_state(session_state)
        metadata = dict(validated_state.metadata or {})

        turns = _extract_turns(metadata)
        recent_turns = turns[-max_turns:]

        user_profile = _extract_user_profile(metadata)
        memory_summary = metadata.get("memory_summary")

        metadata_snapshot = {
            "memory_summary": memory_summary,
            "latest_user_message": new_user_message,
            "turn_count_total": len(turns),
            "turn_count_in_context": len(recent_turns),
            "metadata_snapshot": dict(metadata),
        }

        context = ConversationContext(
            session_id=validated_state.session_id,
            state=validated_state.state,
            turns=recent_turns,
            user_profile=user_profile,
            metadata=metadata_snapshot,
        )

        logger.debug(
            "Built context session_id=%s state=%s turns=%s",
            context.session_id,
            context.state.value,
            len(context.turns),
        )
        return context
    except ContextBuildError:
        raise
    except ValidationError as exc:
        logger.warning("Context model validation failed: %s", exc.errors())
        raise ContextBuildError("Malformed data while building conversation context.") from exc
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("Unexpected failure while building context.")
        raise ContextBuildError("Failed to build conversation context.") from exc


def _validate_session_state(session_state: SessionState) -> SessionState:
    if isinstance(session_state, SessionState):
        return session_state
    raise ContextBuildError("session_state must be a SessionState instance.")


def _extract_turns(metadata: dict[str, Any]) -> list[ConversationTurn]:
    raw_turns = metadata.get("turns", [])
    if raw_turns in (None, []):
        return []
    if not isinstance(raw_turns, list):
        raise ContextBuildError("session_state.metadata['turns'] must be a list.")

    turns: list[ConversationTurn] = []
    for item in raw_turns:
        if isinstance(item, ConversationTurn):
            turns.append(item)
        elif isinstance(item, dict):
            turns.append(ConversationTurn.model_validate(item))
        else:
            raise ContextBuildError("Invalid turn entry in session_state.metadata['turns'].")
    return turns


def _extract_user_profile(metadata: dict[str, Any]) -> UserProfile:
    raw_profile = metadata.get("user_profile")
    if raw_profile is None:
        return UserProfile()
    if isinstance(raw_profile, UserProfile):
        return raw_profile
    if isinstance(raw_profile, dict):
        return UserProfile.model_validate(raw_profile)
    raise ContextBuildError("session_state.metadata['user_profile'] must be an object.")


class ConversationContextManager:
    """Builds context objects for dialogue generation."""

    def build_context(self, *, session_id: UUID, state: str, message: str) -> ConversationContext:
        """Backward-compatible context builder for earlier service calls."""
        try:
            session_state = SessionState(
                session_id=session_id,
                state=ConversationState(state),
                metadata={},
            )
        except ValueError:
            logger.warning("Invalid state passed to compatibility build_context: %s", state)
            session_state = SessionState(
                session_id=session_id,
                state=ConversationState.START,
                metadata={},
            )
        return build_context(session_state=session_state, new_user_message=message, max_turns=10)

    def build_from_session_state(
        self,
        session_state: SessionState,
        new_user_message: str,
        max_turns: int = 10,
    ) -> ConversationContext:
        """Build context from full session state payload."""
        return build_context(
            session_state=session_state,
            new_user_message=new_user_message,
            max_turns=max_turns,
        )

    def to_llm_payload(self, context: ConversationContext) -> dict[str, Any]:
        """Convert context to an LLM-consumable payload."""
        return {
            "session_id": str(context.session_id),
            "state": context.state.value,
            "metadata": dict(context.metadata),
            "turns": [
                {
                    "role": turn.role.value,
                    "message": turn.message,
                    "timestamp": turn.timestamp.isoformat(),
                    "metadata": dict(turn.metadata),
                }
                for turn in context.turns
            ],
            "user_profile": context.user_profile.model_dump(mode="json"),
        }
