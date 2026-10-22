"""Validation layer for prompt-orchestration build requests.

Validation stays domain-local and reusable. It intentionally excludes transport
concerns such as HTTP request/response mapping.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from app.prompt_orchestration.context_assembler import ContextAssemblyLimits
from app.prompt_orchestration.context_models import PromptContextEnvelope
from app.prompt_orchestration.exceptions import PromptOrchestrationApplicationError
from app.prompt_orchestration.models import PromptOrchestrationRequest
from app.prompt_orchestration.output_contract_engine import OutputResponseFormat


def _to_frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _normalized_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized.lower() if normalized else None
    text = str(value).strip()
    return text.lower() if text else None


class PromptValidationErrorCode(StrEnum):
    """Typed error codes for prompt-build request validation."""

    REQUIRED_FIELD_MISSING = "required_field_missing"
    INVALID_ENUM_VALUE = "invalid_enum_value"
    STRATEGY_PREREQUISITE_FAILED = "strategy_prerequisite_failed"
    OUTPUT_CONTRACT_INCOMPATIBLE = "output_contract_incompatible"
    CONTEXT_BUDGET_EXCEEDED = "context_budget_exceeded"


@dataclass(frozen=True, slots=True)
class PromptValidationIssue:
    """Single validation issue discovered during request validation."""

    code: PromptValidationErrorCode
    field: str
    message: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.field.strip():
            raise ValueError("`field` must be non-empty for PromptValidationIssue.")
        if not self.message.strip():
            raise ValueError("`message` must be non-empty for PromptValidationIssue.")
        object.__setattr__(self, "field", self.field.strip())
        object.__setattr__(self, "message", self.message.strip())
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


class PromptRequestValidationError(PromptOrchestrationApplicationError):
    """Typed exception raised when validation issues are present."""

    def __init__(self, issues: Iterable[PromptValidationIssue]) -> None:
        normalized = tuple(issues)
        if not normalized:
            raise ValueError("PromptRequestValidationError requires at least one issue.")
        self.issues = normalized
        message = "; ".join(f"[{issue.code.value}] {issue.field}: {issue.message}" for issue in normalized)
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class PromptBuildValidationRequest:
    """Input contract for modular prompt-build request validation."""

    request: PromptOrchestrationRequest
    context: PromptContextEnvelope
    template_variables: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "template_variables", _to_frozen_mapping(self.template_variables))


class PromptBuildValidationRule(ABC):
    """Base class for a reusable prompt-build validation rule."""

    @abstractmethod
    def validate(self, payload: PromptBuildValidationRequest) -> tuple[PromptValidationIssue, ...]:
        """Return zero or more issues discovered by this rule."""


class RequiredFieldsValidationRule(PromptBuildValidationRule):
    """Validates required request fields for orchestration execution."""

    def validate(self, payload: PromptBuildValidationRequest) -> tuple[PromptValidationIssue, ...]:
        issues: list[PromptValidationIssue] = []
        if payload.request.request_id is None or not payload.request.request_id.strip():
            issues.append(
                PromptValidationIssue(
                    code=PromptValidationErrorCode.REQUIRED_FIELD_MISSING,
                    field="request.request_id",
                    message="request_id is required for orchestration and auditability.",
                )
            )

        if not payload.request.user_input.strip():
            issues.append(
                PromptValidationIssue(
                    code=PromptValidationErrorCode.REQUIRED_FIELD_MISSING,
                    field="request.user_input",
                    message="user_input must be a non-empty string.",
                )
            )

        return tuple(issues)


class StrategyPrerequisitesValidationRule(PromptBuildValidationRule):
    """Validates strategy-specific prerequisites from request metadata and context."""

    def validate(self, payload: PromptBuildValidationRequest) -> tuple[PromptValidationIssue, ...]:
        metadata = payload.request.metadata
        interaction_type = _normalized_optional_str(metadata.get("interaction_type"))
        intent = _normalized_optional_str(metadata.get("intent"))
        onboarding_stage = _normalized_optional_str(metadata.get("onboarding_stage"))

        has_retrieved_context = bool(payload.context.authoritative.retrieved_chunks)
        has_history = bool(payload.context.conversational.recent_messages) or (
            payload.context.conversational.memory_summary is not None
        )

        issues: list[PromptValidationIssue] = []

        if interaction_type == "summarization" and not has_history and not has_retrieved_context:
            issues.append(
                PromptValidationIssue(
                    code=PromptValidationErrorCode.STRATEGY_PREREQUISITE_FAILED,
                    field="request.metadata.interaction_type",
                    message="summarization requires conversation history or retrieved context.",
                )
            )

        if interaction_type == "onboarding" and onboarding_stage == "completed":
            issues.append(
                PromptValidationIssue(
                    code=PromptValidationErrorCode.STRATEGY_PREREQUISITE_FAILED,
                    field="request.metadata.onboarding_stage",
                    message="onboarding interaction is invalid when onboarding_stage is completed.",
                )
            )

        if interaction_type == "qna" and intent == "summarize":
            issues.append(
                PromptValidationIssue(
                    code=PromptValidationErrorCode.STRATEGY_PREREQUISITE_FAILED,
                    field="request.metadata.intent",
                    message="qna interaction cannot use summarize intent.",
                )
            )

        return tuple(issues)


class OutputContractCompatibilityValidationRule(PromptBuildValidationRule):
    """Validates output contract compatibility constraints from request metadata."""

    def validate(self, payload: PromptBuildValidationRequest) -> tuple[PromptValidationIssue, ...]:
        metadata = payload.request.metadata
        output_format_raw = _normalized_optional_str(metadata.get("output_format")) or OutputResponseFormat.PLAIN_TEXT.value

        issues: list[PromptValidationIssue] = []
        try:
            output_format = OutputResponseFormat(output_format_raw)
        except ValueError:
            issues.append(
                PromptValidationIssue(
                    code=PromptValidationErrorCode.INVALID_ENUM_VALUE,
                    field="request.metadata.output_format",
                    message=(
                        f"Unsupported output_format `{output_format_raw}`. "
                        f"Supported values: {', '.join(item.value for item in OutputResponseFormat)}."
                    ),
                )
            )
            return tuple(issues)

        has_json_schema = metadata.get("json_schema") is not None
        json_required_fields = metadata.get("json_required_fields", ())

        if output_format is OutputResponseFormat.JSON_SCHEMA and not has_json_schema:
            issues.append(
                PromptValidationIssue(
                    code=PromptValidationErrorCode.OUTPUT_CONTRACT_INCOMPATIBLE,
                    field="request.metadata.json_schema",
                    message="json_schema is required when output_format is json_schema.",
                )
            )

        if output_format is not OutputResponseFormat.JSON_SCHEMA and has_json_schema:
            issues.append(
                PromptValidationIssue(
                    code=PromptValidationErrorCode.OUTPUT_CONTRACT_INCOMPATIBLE,
                    field="request.metadata.json_schema",
                    message="json_schema is only valid when output_format is json_schema.",
                )
            )

        if output_format in {OutputResponseFormat.PLAIN_TEXT, OutputResponseFormat.MARKDOWN} and json_required_fields:
            issues.append(
                PromptValidationIssue(
                    code=PromptValidationErrorCode.OUTPUT_CONTRACT_INCOMPATIBLE,
                    field="request.metadata.json_required_fields",
                    message="json_required_fields are only valid for JSON output formats.",
                )
            )

        fields_issues = self._validate_json_required_fields(json_required_fields)
        issues.extend(fields_issues)

        max_response_chars = metadata.get("max_response_chars")
        if max_response_chars is not None and (not isinstance(max_response_chars, int) or max_response_chars <= 0):
            issues.append(
                PromptValidationIssue(
                    code=PromptValidationErrorCode.OUTPUT_CONTRACT_INCOMPATIBLE,
                    field="request.metadata.max_response_chars",
                    message="max_response_chars must be a positive integer when provided.",
                )
            )

        return tuple(issues)

    def _validate_json_required_fields(self, value: Any) -> tuple[PromptValidationIssue, ...]:
        if value is None:
            return ()

        if not isinstance(value, (list, tuple)):
            return (
                PromptValidationIssue(
                    code=PromptValidationErrorCode.OUTPUT_CONTRACT_INCOMPATIBLE,
                    field="request.metadata.json_required_fields",
                    message="json_required_fields must be a list or tuple of non-empty strings.",
                ),
            )

        normalized: list[str] = []
        issues: list[PromptValidationIssue] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                issues.append(
                    PromptValidationIssue(
                        code=PromptValidationErrorCode.OUTPUT_CONTRACT_INCOMPATIBLE,
                        field=f"request.metadata.json_required_fields[{index}]",
                        message="Each required field must be a non-empty string.",
                    )
                )
                continue
            normalized.append(item.strip())

        if len(normalized) != len(set(normalized)):
            issues.append(
                PromptValidationIssue(
                    code=PromptValidationErrorCode.OUTPUT_CONTRACT_INCOMPATIBLE,
                    field="request.metadata.json_required_fields",
                    message="json_required_fields must not contain duplicates.",
                )
            )

        return tuple(issues)


class ContextBudgetValidationRule(PromptBuildValidationRule):
    """Validates context payload against configured assembly budgets."""

    def __init__(self, limits: ContextAssemblyLimits | None = None) -> None:
        self._limits = limits or ContextAssemblyLimits()

    def validate(self, payload: PromptBuildValidationRequest) -> tuple[PromptValidationIssue, ...]:
        context = payload.context
        limits = self._limits
        issues: list[PromptValidationIssue] = []

        authoritative_count = len(context.authoritative.retrieved_chunks)
        if authoritative_count > limits.max_authoritative_chunks:
            issues.append(
                self._budget_issue(
                    field="context.authoritative.retrieved_chunks",
                    actual=authoritative_count,
                    limit=limits.max_authoritative_chunks,
                )
            )

        authoritative_chars = sum(len(chunk.content) + len(chunk.citation or "") for chunk in context.authoritative.retrieved_chunks)
        if authoritative_chars > limits.max_authoritative_chars:
            issues.append(
                self._budget_issue(
                    field="context.authoritative.char_count",
                    actual=authoritative_chars,
                    limit=limits.max_authoritative_chars,
                )
            )

        conversational_count = len(context.conversational.recent_messages)
        if conversational_count > limits.max_conversational_messages:
            issues.append(
                self._budget_issue(
                    field="context.conversational.recent_messages",
                    actual=conversational_count,
                    limit=limits.max_conversational_messages,
                )
            )

        summary_chars = len(context.conversational.memory_summary.summary) if context.conversational.memory_summary else 0
        conversational_chars = summary_chars + sum(
            len(item.message.content) for item in context.conversational.recent_messages
        )
        if conversational_chars > limits.max_conversational_chars:
            issues.append(
                self._budget_issue(
                    field="context.conversational.char_count",
                    actual=conversational_chars,
                    limit=limits.max_conversational_chars,
                )
            )

        personalization_entries = self._personalization_entry_count(payload)
        if personalization_entries > limits.max_personalization_entries:
            issues.append(
                self._budget_issue(
                    field="context.personalization.entries",
                    actual=personalization_entries,
                    limit=limits.max_personalization_entries,
                )
            )

        operational_count = len(context.authoritative.policy_constraints) + len(context.authoritative.tool_results)
        if operational_count > limits.max_operational_constraints:
            issues.append(
                self._budget_issue(
                    field="context.operational.entries",
                    actual=operational_count,
                    limit=limits.max_operational_constraints,
                )
            )

        operational_chars = sum(len(item.instruction) for item in context.authoritative.policy_constraints) + sum(
            len(item.summary) + len(item.error_message or "") for item in context.authoritative.tool_results
        )
        if operational_chars > limits.max_operational_chars:
            issues.append(
                self._budget_issue(
                    field="context.operational.char_count",
                    actual=operational_chars,
                    limit=limits.max_operational_chars,
                )
            )

        personalization_chars = self._personalization_char_count(payload)
        total_chars = authoritative_chars + conversational_chars + personalization_chars + operational_chars
        if total_chars > limits.max_total_chars:
            issues.append(
                self._budget_issue(
                    field="context.total_char_count",
                    actual=total_chars,
                    limit=limits.max_total_chars,
                )
            )

        return tuple(issues)

    def _personalization_entry_count(self, payload: PromptBuildValidationRequest) -> int:
        profile = payload.context.personalization.user_profile
        if profile is None:
            return 0

        count = len(profile.preferences)
        if profile.preferred_language:
            count += 1
        if profile.tone_preference:
            count += 1
        if profile.expertise_level:
            count += 1
        return count

    def _personalization_char_count(self, payload: PromptBuildValidationRequest) -> int:
        profile = payload.context.personalization.user_profile
        if profile is None:
            return 0

        count = 0
        if profile.preferred_language:
            count += len(profile.preferred_language)
        if profile.tone_preference:
            count += len(profile.tone_preference)
        if profile.expertise_level:
            count += len(profile.expertise_level)

        for key, value in profile.preferences.items():
            count += len(str(key)) + len(str(value))

        return count

    def _budget_issue(self, *, field: str, actual: int, limit: int) -> PromptValidationIssue:
        return PromptValidationIssue(
            code=PromptValidationErrorCode.CONTEXT_BUDGET_EXCEEDED,
            field=field,
            message=f"Context budget exceeded: got {actual}, limit is {limit}.",
            metadata={"actual": actual, "limit": limit},
        )


class PromptBuildRequestValidator:
    """Composable validator that executes modular prompt-build validation rules."""

    def __init__(self, rules: tuple[PromptBuildValidationRule, ...]) -> None:
        self._rules = rules

    @classmethod
    def default(cls, *, limits: ContextAssemblyLimits | None = None) -> PromptBuildRequestValidator:
        return cls(
            rules=(
                RequiredFieldsValidationRule(),
                StrategyPrerequisitesValidationRule(),
                OutputContractCompatibilityValidationRule(),
                ContextBudgetValidationRule(limits=limits),
            )
        )

    def validate(self, payload: PromptBuildValidationRequest) -> None:
        issues: list[PromptValidationIssue] = []
        for rule in self._rules:
            issues.extend(rule.validate(payload))

        if issues:
            raise PromptRequestValidationError(issues)
