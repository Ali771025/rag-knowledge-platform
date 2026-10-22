"""Deterministic conversation memory retention policy utilities."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.conversation_memory.exceptions import MemoryPolicyError
from app.conversation_memory.models import ConversationMemoryDecision, ConversationState, ConversationTurn, SessionState

logger = logging.getLogger(__name__)


def summarize_turns(turns: list[ConversationTurn]) -> str:
    """Create a deterministic text summary from a list of conversation turns."""
    if not turns:
        return ""

    lines: list[str] = []
    for index, turn in enumerate(turns, start=1):
        normalized = re.sub(r"\s+", " ", turn.message).strip()
        clipped = normalized[:240]
        line = f"{index}. {turn.role.value}: {clipped}"
        lines.append(line)
    return " | ".join(lines)


def apply_memory_policy(session_state: SessionState, max_turns: int = 10) -> SessionState:
    """
    Keep only the most recent ``max_turns`` in active history and summarize older turns.

    The active history is read/written at ``session_state.metadata['turns']``.
    Older turns are appended into ``session_state.metadata['memory_summary']``.
    """
    if max_turns <= 0:
        raise MemoryPolicyError("max_turns must be greater than zero.")

    try:
        updated_state = session_state.model_copy(deep=True)
        metadata: dict[str, Any] = dict(updated_state.metadata or {})
        raw_turns = metadata.get("turns", [])
        if raw_turns in (None, []):
            logger.debug("Memory policy skipped: no turns in metadata.")
            return updated_state

        if not isinstance(raw_turns, list):
            raise MemoryPolicyError("metadata['turns'] must be a list.")

        parsed_turns: list[ConversationTurn] = []
        for item in raw_turns:
            if isinstance(item, ConversationTurn):
                parsed_turns.append(item)
                continue
            if isinstance(item, dict):
                parsed_turns.append(ConversationTurn.model_validate(item))
                continue
            raise MemoryPolicyError("Unsupported turn payload type in metadata['turns'].")

        turn_count = len(parsed_turns)
        if turn_count <= max_turns:
            logger.debug("Memory policy no-op: turn_count=%s max_turns=%s", turn_count, max_turns)
            return updated_state

        archived_turns = parsed_turns[:-max_turns]
        active_turns = parsed_turns[-max_turns:]

        new_summary = summarize_turns(archived_turns)
        existing_summary = str(metadata.get("memory_summary", "")).strip()
        if existing_summary and new_summary:
            merged_summary = f"{existing_summary}\n---\n{new_summary}"
        else:
            merged_summary = existing_summary or new_summary

        metadata["memory_summary"] = merged_summary
        metadata["turns"] = [turn.model_dump(mode="json") for turn in active_turns]

        updated_state.metadata = metadata
        updated_state.updated_at = datetime.now(timezone.utc)

        logger.info(
            "Applied memory policy: archived=%s active=%s session_id=%s",
            len(archived_turns),
            len(active_turns),
            updated_state.session_id,
        )
        return updated_state
    except MemoryPolicyError:
        raise
    except ValidationError as exc:
        logger.warning("Turn payload validation failed during memory policy: %s", exc.errors())
        raise MemoryPolicyError("Invalid turn payload in session metadata.") from exc
    except Exception as exc:  # pragma: no cover - defensive safety net
        logger.exception("Unexpected failure in apply_memory_policy.")
        raise MemoryPolicyError("Failed to apply memory policy.") from exc


class MemoryPolicy:
    """Compatibility wrapper for memory policy operations."""

    def decide(self, *, current_state: str, next_state: str) -> ConversationMemoryDecision:
        """Return a simple persist decision for state transitions."""
        try:
            state = ConversationState(next_state)
        except ValueError:
            state = ConversationState.START

        return ConversationMemoryDecision(
            next_state=state,
            should_persist=True,
            actions=[f"prompt:{state.value}"] if current_state == next_state else [],
        )

    def apply_memory_policy(self, session_state: SessionState, max_turns: int = 10) -> SessionState:
        """Apply deterministic retention policy to session state."""
        return apply_memory_policy(session_state=session_state, max_turns=max_turns)
