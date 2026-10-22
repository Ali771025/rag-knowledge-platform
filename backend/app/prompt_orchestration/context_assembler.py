"""Deterministic context normalization, prioritization, and trimming."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from app.prompt_orchestration.context_models import (
    PolicyConstraint,
    PromptContextEnvelope,
    RecentMessage,
    RetrievedChunk,
    ToolResult,
    ToolResultStatus,
)
from app.prompt_orchestration.exceptions import PromptContractError


def _validate_positive(value: int, field_name: str) -> int:
    if value <= 0:
        raise PromptContractError(f"`{field_name}` must be greater than zero.")
    return value


def _to_frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _clip_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    suffix = "..."
    if max_chars <= len(suffix):
        return value[:max_chars]
    return value[: max_chars - len(suffix)] + suffix


@dataclass(frozen=True, slots=True)
class ContextAssemblyLimits:
    """Configurable deterministic budgets for context assembly."""

    max_authoritative_chunks: int = 8
    max_authoritative_chars: int = 5000
    max_conversational_messages: int = 8
    max_conversational_chars: int = 2500
    max_personalization_entries: int = 12
    max_operational_constraints: int = 8
    max_operational_chars: int = 2500
    max_total_chars: int = 9000

    def __post_init__(self) -> None:
        _validate_positive(self.max_authoritative_chunks, "max_authoritative_chunks")
        _validate_positive(self.max_authoritative_chars, "max_authoritative_chars")
        _validate_positive(self.max_conversational_messages, "max_conversational_messages")
        _validate_positive(self.max_conversational_chars, "max_conversational_chars")
        _validate_positive(self.max_personalization_entries, "max_personalization_entries")
        _validate_positive(self.max_operational_constraints, "max_operational_constraints")
        _validate_positive(self.max_operational_chars, "max_operational_chars")
        _validate_positive(self.max_total_chars, "max_total_chars")


@dataclass(frozen=True, slots=True)
class OperationalConstraintsContext:
    """Operational policy and tool-signal context category."""

    policy_constraints: tuple[PolicyConstraint, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()


@dataclass(frozen=True, slots=True)
class AssembledPersonalizationContext:
    """Trimmed personalization payload for prompt construction."""

    user_profile_fields: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "user_profile_fields", _to_frozen_mapping(self.user_profile_fields))


@dataclass(frozen=True, slots=True)
class AssembledContext:
    """Normalized and trimmed context categories ready for prompt building."""

    authoritative_chunks: tuple[RetrievedChunk, ...]
    conversational_messages: tuple[RecentMessage, ...]
    personalization: AssembledPersonalizationContext
    operational_constraints: OperationalConstraintsContext
    notes: tuple[str, ...] = ()
    total_char_count: int = 0

    def __post_init__(self) -> None:
        if self.total_char_count < 0:
            raise PromptContractError("`total_char_count` cannot be negative.")


class ContextAssembler:
    """Assembles structured context with deterministic ordering and trimming."""

    def __init__(self, limits: ContextAssemblyLimits | None = None) -> None:
        self.limits = limits or ContextAssemblyLimits()

    def assemble(self, envelope: PromptContextEnvelope) -> AssembledContext:
        notes: list[str] = []

        authoritative_chunks, authoritative_chars, chunk_trimmed = self._assemble_authoritative(
            envelope.authoritative.retrieved_chunks
        )
        if chunk_trimmed:
            notes.append("Authoritative chunks trimmed by configured limits.")

        conversational_messages, conversational_chars, messages_trimmed = self._assemble_conversational(envelope)
        if messages_trimmed:
            notes.append("Conversational context trimmed by configured limits.")

        personalization = self._assemble_personalization(envelope)
        personalization_chars = self._estimate_mapping_chars(personalization.user_profile_fields)
        if envelope.personalization.user_profile is not None and len(
            envelope.personalization.user_profile.preferences
        ) + 3 > self.limits.max_personalization_entries:
            notes.append("Personalization preferences trimmed by configured limits.")

        operational_constraints, operational_chars, operational_trimmed = self._assemble_operational(envelope)
        if operational_trimmed:
            notes.append("Operational constraints trimmed by configured limits.")

        total = authoritative_chars + conversational_chars + personalization_chars + operational_chars
        if total > self.limits.max_total_chars:
            notes.append("Total context exceeded max_total_chars; applying deterministic final trim.")
            authoritative_chunks, authoritative_chars = self._trim_authoritative_to_budget(
                authoritative_chunks, self.limits.max_authoritative_chars // 2
            )
            total = authoritative_chars + conversational_chars + personalization_chars + operational_chars

        return AssembledContext(
            authoritative_chunks=authoritative_chunks,
            conversational_messages=conversational_messages,
            personalization=personalization,
            operational_constraints=operational_constraints,
            notes=tuple(notes),
            total_char_count=total,
        )

    def _assemble_authoritative(
        self, chunks: tuple[RetrievedChunk, ...]
    ) -> tuple[tuple[RetrievedChunk, ...], int, bool]:
        ordered = sorted(chunks, key=lambda item: (-item.relevance_score, item.source_id, item.chunk_id))

        trimmed: list[RetrievedChunk] = []
        used_chars = 0
        max_items = self.limits.max_authoritative_chunks
        max_chars = self.limits.max_authoritative_chars

        for chunk in ordered:
            if len(trimmed) >= max_items:
                break
            chunk_chars = len(chunk.content) + len(chunk.citation or "")
            if chunk_chars > max_chars and not trimmed:
                # Keep at least one chunk by clipping content deterministically.
                clipped_chunk = RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    source_id=chunk.source_id,
                    content=_clip_text(chunk.content, max_chars),
                    relevance_score=chunk.relevance_score,
                    citation=chunk.citation,
                    metadata=chunk.metadata,
                )
                trimmed.append(clipped_chunk)
                used_chars = len(clipped_chunk.content) + len(clipped_chunk.citation or "")
                break
            if used_chars + chunk_chars > max_chars:
                continue
            trimmed.append(chunk)
            used_chars += chunk_chars

        was_trimmed = len(trimmed) != len(chunks)
        return tuple(trimmed), used_chars, was_trimmed

    def _assemble_conversational(
        self, envelope: PromptContextEnvelope
    ) -> tuple[tuple[RecentMessage, ...], int, bool]:
        summary = envelope.conversational.memory_summary.summary if envelope.conversational.memory_summary else ""
        summary_chars = len(summary)
        max_chars = self.limits.max_conversational_chars

        messages = list(envelope.conversational.recent_messages)
        messages.sort(
            key=lambda item: (
                item.occurred_at.isoformat() if item.occurred_at else "",
                item.message.role.value,
                item.message.content,
            )
        )
        # Keep the most recent messages by taking the end slice after deterministic sort.
        if len(messages) > self.limits.max_conversational_messages:
            messages = messages[-self.limits.max_conversational_messages :]

        kept: list[RecentMessage] = []
        used_chars = summary_chars
        for message in messages:
            msg_chars = len(message.message.content)
            if used_chars + msg_chars > max_chars:
                continue
            kept.append(message)
            used_chars += msg_chars

        trimmed = (
            len(kept) != len(envelope.conversational.recent_messages)
            or summary_chars > self.limits.max_conversational_chars
        )
        return tuple(kept), used_chars, trimmed

    def _assemble_personalization(self, envelope: PromptContextEnvelope) -> AssembledPersonalizationContext:
        user_profile = envelope.personalization.user_profile
        if user_profile is None:
            return AssembledPersonalizationContext()

        fields: dict[str, Any] = {}
        if user_profile.preferred_language:
            fields["preferred_language"] = user_profile.preferred_language
        if user_profile.tone_preference:
            fields["tone_preference"] = user_profile.tone_preference
        if user_profile.expertise_level:
            fields["expertise_level"] = user_profile.expertise_level

        remaining_slots = max(self.limits.max_personalization_entries - len(fields), 0)
        for key in sorted(user_profile.preferences.keys())[:remaining_slots]:
            fields[f"pref.{key}"] = user_profile.preferences[key]

        return AssembledPersonalizationContext(user_profile_fields=fields)

    def _assemble_operational(
        self, envelope: PromptContextEnvelope
    ) -> tuple[OperationalConstraintsContext, int, bool]:
        constraints = list(envelope.authoritative.policy_constraints)
        constraints.sort(key=lambda item: (item.strength.value, item.constraint_id))

        tool_results = list(envelope.authoritative.tool_results)
        status_order = {
            ToolResultStatus.ERROR: 0,
            ToolResultStatus.PARTIAL: 1,
            ToolResultStatus.SUCCESS: 2,
        }
        tool_results.sort(key=lambda item: (status_order[item.status], item.tool_name))

        max_items = self.limits.max_operational_constraints
        max_chars = self.limits.max_operational_chars
        used_chars = 0

        kept_constraints: list[PolicyConstraint] = []
        for constraint in constraints:
            if len(kept_constraints) >= max_items:
                break
            constraint_chars = len(constraint.instruction)
            if used_chars + constraint_chars > max_chars:
                continue
            kept_constraints.append(constraint)
            used_chars += constraint_chars

        remaining_slots = max(max_items - len(kept_constraints), 0)
        kept_results: list[ToolResult] = []
        for result in tool_results:
            if len(kept_results) >= remaining_slots:
                break
            result_chars = len(result.summary) + len(result.error_message or "")
            if used_chars + result_chars > max_chars:
                continue
            kept_results.append(result)
            used_chars += result_chars

        trimmed = len(kept_constraints) != len(constraints) or len(kept_results) != len(tool_results)
        return OperationalConstraintsContext(
            policy_constraints=tuple(kept_constraints),
            tool_results=tuple(kept_results),
        ), used_chars, trimmed

    def _trim_authoritative_to_budget(
        self, chunks: tuple[RetrievedChunk, ...], new_budget: int
    ) -> tuple[tuple[RetrievedChunk, ...], int]:
        used = 0
        kept: list[RetrievedChunk] = []
        for chunk in chunks:
            chunk_chars = len(chunk.content) + len(chunk.citation or "")
            if used + chunk_chars > new_budget:
                break
            kept.append(chunk)
            used += chunk_chars
        return tuple(kept), used

    def _estimate_mapping_chars(self, payload: Mapping[str, Any]) -> int:
        count = 0
        for key, value in payload.items():
            count += len(str(key))
            count += len(str(value))
        return count

