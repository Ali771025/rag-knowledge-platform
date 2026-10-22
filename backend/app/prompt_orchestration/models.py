"""Core prompt orchestration domain models.

This module intentionally remains free of API, persistence, and provider-specific
transport concerns. It only defines strongly-typed contracts and local invariants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
import re
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field as PydanticField, field_validator, model_validator

from app.internal.conversion.policy_enums import TriggerType
from app.internal.conversion.policy_enums import JourneyStage as FunnelStage
from app.internal.persona.enums import PersonaModifier
from app.prompt_orchestration.exceptions import PromptContractError

_VARIABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise PromptContractError(f"`{field_name}` must be a non-empty string.")
    return normalized


def _validate_optional_non_empty(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise PromptContractError(f"`{field_name}` cannot be blank when provided.")
    return normalized


def _to_frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _validate_variable_name(name: str) -> str:
    normalized = _validate_non_empty(name, "variable_name")
    if not _VARIABLE_NAME_PATTERN.match(normalized):
        raise PromptContractError(
            f"Invalid template variable `{normalized}`. Use letters, numbers, and underscores only."
        )
    return normalized


class PromptRole(StrEnum):
    """Role for a prompt message."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class OutputFormat(StrEnum):
    """Supported output contract format families."""

    TEXT = "text"
    JSON_OBJECT = "json_object"
    JSON_SCHEMA = "json_schema"


class GroundingMode(StrEnum):
    """Grounding strictness for downstream answer generation."""

    REQUIRED = "required"
    PREFERRED = "preferred"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class TemplateRef:
    """Stable identifier for a prompt template revision."""

    template_id: str
    version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "template_id", _validate_non_empty(self.template_id, "template_id"))
        object.__setattr__(self, "version", _validate_non_empty(self.version, "version"))


@dataclass(frozen=True, slots=True)
class PromptMessage:
    """A normalized prompt message unit."""

    role: PromptRole
    content: str
    name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "content", _validate_non_empty(self.content, "content"))
        object.__setattr__(self, "name", _validate_optional_non_empty(self.name, "name"))

        if self.name and self.role is PromptRole.SYSTEM:
            raise PromptContractError("System messages cannot include a `name` field.")


@dataclass(frozen=True, slots=True)
class OutputContract:
    """Constraints describing the shape of model output."""

    format: OutputFormat = OutputFormat.TEXT
    required_sections: tuple[str, ...] = ()
    json_schema: Mapping[str, Any] | None = None
    max_output_tokens: int | None = None

    def __post_init__(self) -> None:
        sections = tuple(_validate_non_empty(section, "required_sections[]") for section in self.required_sections)
        if len(set(sections)) != len(sections):
            raise PromptContractError("`required_sections` must not contain duplicates.")
        object.__setattr__(self, "required_sections", sections)

        if self.max_output_tokens is not None and self.max_output_tokens <= 0:
            raise PromptContractError("`max_output_tokens` must be greater than zero when provided.")

        if self.format is OutputFormat.JSON_SCHEMA and not self.json_schema:
            raise PromptContractError("`json_schema` is required when output format is `json_schema`.")

        if self.format is OutputFormat.TEXT and self.json_schema is not None:
            raise PromptContractError("`json_schema` is only valid for JSON-based output formats.")

        frozen_schema = None if self.json_schema is None else _to_frozen_mapping(self.json_schema)
        object.__setattr__(self, "json_schema", frozen_schema)


@dataclass(frozen=True, slots=True)
class GroundingPolicy:
    """Rules that govern how tightly outputs must stay grounded in context."""

    mode: GroundingMode = GroundingMode.PREFERRED
    require_citations: bool = False
    min_citations: int = 0
    allow_unverified_claims: bool = False

    def __post_init__(self) -> None:
        if self.min_citations < 0:
            raise PromptContractError("`min_citations` cannot be negative.")

        if self.mode is GroundingMode.DISABLED and self.require_citations:
            raise PromptContractError("Citations cannot be required when grounding is disabled.")

        if self.require_citations and self.min_citations == 0:
            raise PromptContractError("`min_citations` must be at least 1 when citations are required.")

        if self.mode is GroundingMode.REQUIRED and self.allow_unverified_claims:
            raise PromptContractError("`allow_unverified_claims` must be false when grounding mode is required.")


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """Prompt template definition used by the build pipeline."""

    ref: TemplateRef
    instruction_messages: tuple[PromptMessage, ...]
    input_variables: frozenset[str] = field(default_factory=frozenset)
    default_output_contract: OutputContract = field(default_factory=OutputContract)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.instruction_messages:
            raise PromptContractError("`instruction_messages` cannot be empty.")

        variables = frozenset(_validate_variable_name(name) for name in self.input_variables)
        object.__setattr__(self, "input_variables", variables)

        frozen_metadata = _to_frozen_mapping(self.metadata)
        object.__setattr__(self, "metadata", frozen_metadata)


@dataclass(frozen=True, slots=True)
class PromptBuildRequest:
    """Domain request for building a prompt payload."""

    request_id: str
    user_input: str
    template: PromptTemplate
    output_contract: OutputContract
    grounding_policy: GroundingPolicy = field(default_factory=GroundingPolicy)
    template_variables: Mapping[str, Any] = field(default_factory=dict)
    conversation_history: tuple[PromptMessage, ...] = ()
    context_snippets: tuple[str, ...] = ()
    session_id: UUID | None = None
    user_id: UUID | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _validate_non_empty(self.request_id, "request_id"))
        object.__setattr__(self, "user_input", _validate_non_empty(self.user_input, "user_input"))

        frozen_variables = _to_frozen_mapping(self.template_variables)
        object.__setattr__(self, "template_variables", frozen_variables)

        missing_variables = sorted(self.template.input_variables - set(frozen_variables))
        if missing_variables:
            missing = ", ".join(missing_variables)
            raise PromptContractError(f"Missing required template variable(s): {missing}")

        normalized_snippets = tuple(_validate_non_empty(snippet, "context_snippets[]") for snippet in self.context_snippets)
        object.__setattr__(self, "context_snippets", normalized_snippets)


@dataclass(frozen=True, slots=True)
class PromptAuditRecord:
    """Audit-safe trace metadata for a prompt build."""

    request_id: str
    template_ref: TemplateRef
    grounding_mode: GroundingMode
    resolved_variables: tuple[str, ...] = ()
    unresolved_variables: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _validate_non_empty(self.request_id, "request_id"))

        resolved = tuple(_validate_variable_name(name) for name in self.resolved_variables)
        unresolved = tuple(_validate_variable_name(name) for name in self.unresolved_variables)

        overlap = set(resolved).intersection(unresolved)
        if overlap:
            conflict = ", ".join(sorted(overlap))
            raise PromptContractError(f"Variables cannot be both resolved and unresolved: {conflict}")

        normalized_warnings = tuple(_validate_non_empty(note, "warnings[]") for note in self.warnings)

        if self.created_at.tzinfo is None:
            raise PromptContractError("`created_at` must be timezone-aware.")

        object.__setattr__(self, "resolved_variables", resolved)
        object.__setattr__(self, "unresolved_variables", unresolved)
        object.__setattr__(self, "warnings", normalized_warnings)


@dataclass(frozen=True, slots=True)
class PromptBuildResult:
    """Domain result produced by the prompt build stage."""

    request_id: str
    template_ref: TemplateRef
    messages: tuple[PromptMessage, ...]
    output_contract: OutputContract
    grounding_policy: GroundingPolicy
    audit_record: PromptAuditRecord

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _validate_non_empty(self.request_id, "request_id"))
        if not self.messages:
            raise PromptContractError("`messages` cannot be empty.")

        if self.audit_record.request_id != self.request_id:
            raise PromptContractError("`audit_record.request_id` must match `PromptBuildResult.request_id`.")

        if self.audit_record.template_ref != self.template_ref:
            raise PromptContractError("`audit_record.template_ref` must match `PromptBuildResult.template_ref`.")


@dataclass(frozen=True, slots=True)
class PromptOrchestrationRequest:
    """Compatibility request contract retained for protocol stability."""

    session_id: UUID | None
    user_id: UUID | None
    request_id: str | None
    user_input: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _validate_optional_non_empty(self.request_id, "request_id"))
        object.__setattr__(self, "user_input", _validate_non_empty(self.user_input, "user_input"))
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class LLMInferenceRequest:
    """Compatibility inference request retained for protocol stability."""

    messages: tuple[PromptMessage, ...]
    model_hint: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.messages:
            raise PromptContractError("`messages` cannot be empty.")
        object.__setattr__(self, "model_hint", _validate_optional_non_empty(self.model_hint, "model_hint"))

        if self.temperature is not None and (self.temperature < 0 or self.temperature > 2):
            raise PromptContractError("`temperature` must be between 0 and 2.")

        if self.max_tokens is not None and self.max_tokens <= 0:
            raise PromptContractError("`max_tokens` must be greater than zero when provided.")

        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class RetrievalContextSnapshot:
    """Read-model snapshot retained for compatibility with protocol boundaries."""

    snippets: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ConversationContextSnapshot:
    """Read-model snapshot retained for compatibility with protocol boundaries."""

    history: tuple[PromptMessage, ...] = ()
    summary: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", _validate_optional_non_empty(self.summary, "summary"))
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class UserContextSnapshot:
    """Read-model snapshot retained for compatibility with protocol boundaries."""

    preferences: Mapping[str, Any] = field(default_factory=dict)
    safety_overrides: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "preferences", _to_frozen_mapping(self.preferences))
        object.__setattr__(self, "safety_overrides", _to_frozen_mapping(self.safety_overrides))
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class LLMInferenceResponse:
    """Compatibility response contract retained for downstream protocol import stability."""

    text: str
    provider_response_id: str | None = None
    usage: Mapping[str, int] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _validate_non_empty(self.text, "text"))
        object.__setattr__(self, "provider_response_id", _validate_optional_non_empty(self.provider_response_id, "provider_response_id"))
        object.__setattr__(self, "usage", _to_frozen_mapping(self.usage))
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class OrchestratedPromptPackage:
    """Compatibility package retained for existing type imports."""

    messages: tuple[PromptMessage, ...]
    retrieval_context: RetrievalContextSnapshot | None = None
    conversation_context: ConversationContextSnapshot | None = None
    user_context: UserContextSnapshot | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.messages:
            raise PromptContractError("`messages` cannot be empty.")
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


class TriggerSelectionInput(BaseModel):
    """Shared typed input contract for policy-driven trigger selection."""

    persona: str = PydanticField(..., min_length=1, max_length=64)
    confidence: float = PydanticField(..., ge=0.0, le=1.0)
    intent: str = PydanticField(default="", max_length=256)
    stage: FunnelStage
    trust_score: float = PydanticField(..., ge=0.0, le=1.0)
    modifiers: list[PersonaModifier] = PydanticField(default_factory=list)
    rejection_history: dict[TriggerType, int] = PydanticField(default_factory=dict)
    session_trigger_usage: dict[TriggerType, int] = PydanticField(default_factory=dict)
    capacity_flags: dict[TriggerType, bool] = PydanticField(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("rejection_history", "session_trigger_usage")
    @classmethod
    def _validate_non_negative_counts(cls, value: dict[TriggerType, int]) -> dict[TriggerType, int]:
        if any(count < 0 for count in value.values()):
            raise ValueError("history and usage counts must be non-negative")
        return value


class TriggerSelectionOutput(BaseModel):
    """Shared typed output contract for trigger selector orchestration metadata."""

    primary_trigger: TriggerType
    secondary_trigger: TriggerType | None = None
    intensity: float = PydanticField(..., ge=0.0, le=1.0)
    selected_triggers: list[TriggerType] = PydanticField(..., min_length=1, max_length=2)
    reasoning: dict[str, Any] = PydanticField(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_selected_alignment(self) -> "TriggerSelectionOutput":
        if self.selected_triggers[0] is not self.primary_trigger:
            raise ValueError("selected_triggers must list the primary trigger first")
        if self.secondary_trigger is not None and self.secondary_trigger not in self.selected_triggers:
            raise ValueError("secondary_trigger must be included in selected_triggers when present")
        if self.secondary_trigger is None and len(self.selected_triggers) > 1:
            raise ValueError("secondary_trigger is required when two selected triggers are returned")
        return self


class TriggerIntensityLevel(StrEnum):
    """Normalized intensity tiers used by trigger template resolver."""

    SOFT = "soft"
    MEDIUM = "medium"
    HIGH = "high"


class PromptOrchestrationMeta(BaseModel):
    """Structured metadata describing trigger guidance for prompt composition."""

    triggers: list[TriggerType] = PydanticField(..., min_length=1, max_length=2)
    intensity: float = PydanticField(..., ge=0.0, le=1.0)
    intensity_level: TriggerIntensityLevel
    tone: str = PydanticField(..., min_length=1, max_length=64)
    proof_style: str = PydanticField(..., min_length=1, max_length=64)
    cta_style: str = PydanticField(..., min_length=1, max_length=64)
    trigger_fragments: list[str] = PydanticField(..., min_length=1, max_length=2)
    conversion_decision: dict[str, Any] | None = None
    metadata: dict[str, Any] = PydanticField(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
