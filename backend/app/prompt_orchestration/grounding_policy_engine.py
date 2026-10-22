"""Prompt-level grounding policy constraint engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from app.prompt_orchestration.exceptions import PromptContractError


def _validate_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise PromptContractError(f"`{field_name}` must be a non-empty string.")
    return normalized


def _to_frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


class GroundingPolicyMode(StrEnum):
    """Supported grounding policy modes."""

    STRICT_GROUNDED = "strict_grounded"
    GROUNDED_PREFERRED = "grounded_preferred"
    OPEN_GENERATION_LIMITED = "open_generation_limited"


class InsufficientContextPolicy(StrEnum):
    """Fallback behavior when authoritative context is insufficient."""

    REFUSE = "refuse"
    ASK_CLARIFYING_QUESTION = "ask_clarifying_question"
    ANSWER_WITH_DISCLAIMER = "answer_with_disclaimer"


@dataclass(frozen=True, slots=True)
class GroundingPolicyRequest:
    """Inputs used by the grounding policy engine."""

    mode: GroundingPolicyMode
    insufficient_context_policy: InsufficientContextPolicy
    has_authoritative_context: bool
    authoritative_context_count: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.authoritative_context_count < 0:
            raise PromptContractError("`authoritative_context_count` cannot be negative.")
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class GroundingPromptConstraints:
    """Structured constraints to inject into prompt construction."""

    mode: GroundingPolicyMode
    insufficient_context_policy: InsufficientContextPolicy
    instruction_lines: tuple[str, ...]
    requires_citations: bool
    forbid_ungrounded_claims: bool
    refusal_required_when_insufficient: bool
    clarifying_question_required_when_insufficient: bool
    disclaimer_required_when_insufficient: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.instruction_lines:
            raise PromptContractError("`instruction_lines` cannot be empty.")
        normalized_lines = tuple(_validate_non_empty(line, "instruction_lines[]") for line in self.instruction_lines)
        object.__setattr__(self, "instruction_lines", normalized_lines)
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


class GroundingPolicyEngine:
    """Deterministic policy engine for anti-hallucination prompt constraints."""

    def build_constraints(self, request: GroundingPolicyRequest) -> GroundingPromptConstraints:
        context_is_sufficient = request.has_authoritative_context and request.authoritative_context_count > 0
        instructions = list(self._base_mode_instructions(request.mode))

        refusal_required = False
        clarifying_required = False
        disclaimer_required = False

        if not context_is_sufficient:
            fallback_instruction, refusal_required, clarifying_required, disclaimer_required = (
                self._insufficient_context_instruction(request.insufficient_context_policy)
            )
            instructions.append(fallback_instruction)
            instructions.append("Do not fabricate missing facts, references, or citations.")

        requires_citations = request.mode is GroundingPolicyMode.STRICT_GROUNDED
        forbid_ungrounded = request.mode in {
            GroundingPolicyMode.STRICT_GROUNDED,
            GroundingPolicyMode.GROUNDED_PREFERRED,
        }

        return GroundingPromptConstraints(
            mode=request.mode,
            insufficient_context_policy=request.insufficient_context_policy,
            instruction_lines=tuple(instructions),
            requires_citations=requires_citations,
            forbid_ungrounded_claims=forbid_ungrounded,
            refusal_required_when_insufficient=refusal_required,
            clarifying_question_required_when_insufficient=clarifying_required,
            disclaimer_required_when_insufficient=disclaimer_required,
            metadata={
                "authoritative_context_count": request.authoritative_context_count,
                "context_is_sufficient": context_is_sufficient,
            },
        )

    def _base_mode_instructions(self, mode: GroundingPolicyMode) -> tuple[str, ...]:
        if mode is GroundingPolicyMode.STRICT_GROUNDED:
            return (
                "Answer only from authoritative context provided in this request.",
                "Cite supporting context for each material factual claim.",
                "If evidence is missing, do not infer facts from outside knowledge.",
            )
        if mode is GroundingPolicyMode.GROUNDED_PREFERRED:
            return (
                "Prioritize authoritative context as the primary evidence source.",
                "If context is partial, keep claims conservative and explicitly mark uncertainty.",
                "Use citations when context evidence is available.",
            )
        return (
            "You may generate a helpful response, but avoid high-confidence unsupported factual claims.",
            "State uncertainty when evidence is weak or absent.",
            "Never fabricate citations or present guessed facts as verified.",
        )

    def _insufficient_context_instruction(
        self, policy: InsufficientContextPolicy
    ) -> tuple[str, bool, bool, bool]:
        if policy is InsufficientContextPolicy.REFUSE:
            return (
                "If context is insufficient, refuse briefly and request additional authoritative information.",
                True,
                False,
                False,
            )
        if policy is InsufficientContextPolicy.ASK_CLARIFYING_QUESTION:
            return (
                "If context is insufficient, ask one targeted clarifying question before answering.",
                False,
                True,
                False,
            )
        return (
            "If context is insufficient, provide a limited answer with a clear disclaimer about uncertainty.",
            False,
            False,
            True,
        )

