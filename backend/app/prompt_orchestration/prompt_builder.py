"""PromptBuilder v1 for deterministic prompt message assembly."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from app.prompt_orchestration.context_assembler import AssembledContext
from app.prompt_orchestration.exceptions import PromptContractError
from app.prompt_orchestration.grounding_policy_engine import GroundingPromptConstraints
from app.prompt_orchestration.models import (
    GroundingPolicy,
    OutputContract,
    PromptAuditRecord,
    PromptBuildResult,
    PromptMessage,
    PromptRole,
    PromptTemplate,
)
from app.prompt_orchestration.output_contract_engine import OutputPromptConstraints
from app.prompt_orchestration.planner import PromptPlanningResult
from app.prompt_orchestration.template_registry import TemplateLookupResult


def _validate_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise PromptContractError(f"`{field_name}` must be a non-empty string.")
    return normalized


def _to_frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


@dataclass(frozen=True, slots=True)
class PromptBuilderInput:
    """Inputs for deterministic prompt assembly."""

    request_id: str
    user_input: str
    template_lookup: TemplateLookupResult
    planning: PromptPlanningResult
    assembled_context: AssembledContext
    grounding_constraints: GroundingPromptConstraints
    output_constraints: OutputPromptConstraints
    output_contract: OutputContract
    grounding_policy: GroundingPolicy
    template_variables: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _validate_non_empty(self.request_id, "request_id"))
        object.__setattr__(self, "user_input", _validate_non_empty(self.user_input, "user_input"))
        object.__setattr__(self, "template_variables", _to_frozen_mapping(self.template_variables))
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class PromptBuildDraft:
    """PromptBuildResult-ready structure produced by PromptBuilder."""

    request_id: str
    template: PromptTemplate
    messages: tuple[PromptMessage, ...]
    grounding_policy: GroundingPolicy
    output_contract: OutputContract
    resolved_variables: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _validate_non_empty(self.request_id, "request_id"))
        if not self.messages:
            raise PromptContractError("`messages` cannot be empty.")
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))

    def to_prompt_build_result(self) -> PromptBuildResult:
        """Materialize PromptBuildResult with a deterministic audit record."""
        audit = PromptAuditRecord(
            request_id=self.request_id,
            template_ref=self.template.ref,
            grounding_mode=self.grounding_policy.mode,
            resolved_variables=self.resolved_variables,
            warnings=self.warnings,
        )
        return PromptBuildResult(
            request_id=self.request_id,
            template_ref=self.template.ref,
            messages=self.messages,
            output_contract=self.output_contract,
            grounding_policy=self.grounding_policy,
            audit_record=audit,
        )


class PromptBuilder:
    """Assembles ordered, readable, and safe prompt messages deterministically."""

    def build(self, payload: PromptBuilderInput) -> PromptBuildDraft:
        template = payload.template_lookup.record.template
        messages: list[PromptMessage] = []

        messages.append(
            PromptMessage(
                role=PromptRole.SYSTEM,
                content=self._system_prompt(payload),
            )
        )
        messages.append(
            PromptMessage(
                role=PromptRole.SYSTEM,
                content=self._instruction_prompt(template, payload),
            )
        )

        context_blocks = self._context_blocks(payload)
        for block in context_blocks:
            messages.append(PromptMessage(role=PromptRole.SYSTEM, content=block))

        conversation_block = self._conversation_block(payload)
        if conversation_block is not None:
            messages.append(PromptMessage(role=PromptRole.SYSTEM, content=conversation_block))

        messages.append(PromptMessage(role=PromptRole.USER, content=self._user_block(payload)))

        warnings: list[str] = []
        if payload.template_lookup.fallback_used:
            warnings.append(
                "Template fallback used: requested template variant was unavailable and a deterministic fallback was selected."
            )
        warnings.extend(payload.assembled_context.notes)

        resolved_variables = tuple(sorted(payload.template_variables.keys()))
        return PromptBuildDraft(
            request_id=payload.request_id,
            template=template,
            messages=tuple(messages),
            grounding_policy=payload.grounding_policy,
            output_contract=payload.output_contract,
            resolved_variables=resolved_variables,
            warnings=tuple(warnings),
            metadata={
                "selected_strategy": payload.planning.selected_strategy.value,
                "template_key": {
                    "strategy": payload.template_lookup.matched_key.strategy.value,
                    "language": payload.template_lookup.matched_key.language,
                    "version": payload.template_lookup.matched_key.version,
                    "environment": payload.template_lookup.matched_key.environment,
                },
                "context_total_chars": payload.assembled_context.total_char_count,
            },
        )

    def _system_prompt(self, payload: PromptBuilderInput) -> str:
        lines = [
            "# SYSTEM PROMPT",
            "You are a safety-aware assistant. Follow all constraints in this request.",
            "",
            "## Grounding Policy",
        ]
        lines.extend(f"- {line}" for line in payload.grounding_constraints.instruction_lines)
        lines.append("")
        lines.append("## Output Contract")
        lines.extend(f"- {line}" for line in payload.output_constraints.instruction_lines)
        lines.extend(f"- {line}" for line in payload.output_constraints.refusal_lines)
        lines.extend(f"- {line}" for line in payload.output_constraints.style_lines)
        lines.extend(f"- {line}" for line in payload.output_constraints.compliance_lines)
        return "\n".join(lines)

    def _instruction_prompt(self, template: PromptTemplate, payload: PromptBuilderInput) -> str:
        lines = [
            "# DEVELOPER INSTRUCTION PROMPT",
            f"Selected strategy: {payload.planning.selected_strategy.value}",
            "Planning notes:",
        ]
        lines.extend(f"- {note}" for note in payload.planning.planning_notes)
        lines.append("")
        lines.append("Template instructions:")
        for index, message in enumerate(template.instruction_messages, start=1):
            lines.append(f"{index}. [{message.role.value}] {message.content}")
        if payload.template_variables:
            lines.append("")
            lines.append("Resolved template variables:")
            for key in sorted(payload.template_variables.keys()):
                lines.append(f"- {key}: {payload.template_variables[key]}")
        return "\n".join(lines)

    def _context_blocks(self, payload: PromptBuilderInput) -> tuple[str, ...]:
        blocks: list[str] = []

        if payload.assembled_context.authoritative_chunks:
            lines = ["# CONTEXT BLOCK: AUTHORITATIVE SOURCES"]
            for idx, chunk in enumerate(payload.assembled_context.authoritative_chunks, start=1):
                citation = f" | citation: {chunk.citation}" if chunk.citation else ""
                lines.append(
                    f"{idx}. source={chunk.source_id} chunk={chunk.chunk_id} relevance={chunk.relevance_score:.2f}{citation}"
                )
                lines.append(chunk.content)
            blocks.append("\n".join(lines))

        op = payload.assembled_context.operational_constraints
        if op.policy_constraints or op.tool_results:
            lines = ["# CONTEXT BLOCK: OPERATIONAL CONSTRAINTS"]
            for constraint in op.policy_constraints:
                lines.append(f"- policy[{constraint.constraint_id}] ({constraint.strength.value}): {constraint.instruction}")
            for result in op.tool_results:
                err = f" | error={result.error_message}" if result.error_message else ""
                lines.append(f"- tool[{result.tool_name}] status={result.status.value}: {result.summary}{err}")
            blocks.append("\n".join(lines))

        if payload.assembled_context.personalization.user_profile_fields:
            lines = ["# CONTEXT BLOCK: PERSONALIZATION"]
            for key in sorted(payload.assembled_context.personalization.user_profile_fields.keys()):
                lines.append(f"- {key}: {payload.assembled_context.personalization.user_profile_fields[key]}")
            blocks.append("\n".join(lines))

        return tuple(blocks)

    def _conversation_block(self, payload: PromptBuilderInput) -> str | None:
        if not payload.assembled_context.conversational_messages:
            return None

        lines = ["# CONVERSATION BLOCK", "Recent turns (oldest to newest after deterministic trim):"]
        for index, item in enumerate(payload.assembled_context.conversational_messages, start=1):
            lines.append(f"{index}. [{item.message.role.value}] {item.message.content}")
        return "\n".join(lines)

    def _user_block(self, payload: PromptBuilderInput) -> str:
        return "\n".join(
            [
                "# USER BLOCK",
                payload.user_input,
            ]
        )

