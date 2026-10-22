"""Prompt-level output contract engine for format/style/compliance control."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import json
from types import MappingProxyType
from typing import Any, Mapping

from app.prompt_orchestration.exceptions import PromptContractError


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


class OutputResponseFormat(StrEnum):
    """Supported response format contract types."""

    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"
    JSON = "json"
    JSON_SCHEMA = "json_schema"


class RefusalPattern(StrEnum):
    """Safe refusal/deferral patterns."""

    DIRECT_REFUSAL = "direct_refusal"
    SAFE_DEFERRAL = "safe_deferral"


@dataclass(frozen=True, slots=True)
class OutputRefusalPolicy:
    """Policy for safe refusal and deferral responses."""

    allow_refusal: bool = True
    allow_deferral: bool = True
    preferred_pattern: RefusalPattern = RefusalPattern.SAFE_DEFERRAL
    custom_refusal_line: str | None = None
    custom_deferral_line: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "custom_refusal_line", _validate_optional_non_empty(self.custom_refusal_line, "custom_refusal_line")
        )
        object.__setattr__(
            self, "custom_deferral_line", _validate_optional_non_empty(self.custom_deferral_line, "custom_deferral_line")
        )
        if not self.allow_refusal and self.preferred_pattern is RefusalPattern.DIRECT_REFUSAL:
            raise PromptContractError("`preferred_pattern` cannot be direct_refusal when `allow_refusal` is false.")
        if not self.allow_refusal and not self.allow_deferral:
            raise PromptContractError("At least one of refusal or deferral must be allowed.")


@dataclass(frozen=True, slots=True)
class OutputStyleProfile:
    """Style and compliance profile for response shaping."""

    style: str | None = None
    tone: str | None = None
    language: str = "en"
    compliance_constraints: tuple[str, ...] = ()
    max_response_chars: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "style", _validate_optional_non_empty(self.style, "style"))
        object.__setattr__(self, "tone", _validate_optional_non_empty(self.tone, "tone"))
        object.__setattr__(self, "language", _validate_non_empty(self.language, "language").lower())

        constraints = tuple(_validate_non_empty(item, "compliance_constraints[]") for item in self.compliance_constraints)
        object.__setattr__(self, "compliance_constraints", constraints)

        if self.max_response_chars is not None and self.max_response_chars <= 0:
            raise PromptContractError("`max_response_chars` must be greater than zero when provided.")


@dataclass(frozen=True, slots=True)
class OutputContractRequest:
    """Input request for output-contract constraint generation."""

    format: OutputResponseFormat
    style_profile: OutputStyleProfile = field(default_factory=OutputStyleProfile)
    refusal_policy: OutputRefusalPolicy = field(default_factory=OutputRefusalPolicy)
    json_required_fields: tuple[str, ...] = ()
    json_schema: Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required_fields = tuple(_validate_non_empty(item, "json_required_fields[]") for item in self.json_required_fields)
        if len(set(required_fields)) != len(required_fields):
            raise PromptContractError("`json_required_fields` cannot contain duplicates.")
        object.__setattr__(self, "json_required_fields", required_fields)

        if self.format is OutputResponseFormat.JSON_SCHEMA and not self.json_schema:
            raise PromptContractError("`json_schema` is required when format is `json_schema`.")
        if self.format is not OutputResponseFormat.JSON_SCHEMA and self.json_schema is not None:
            raise PromptContractError("`json_schema` is only supported when format is `json_schema`.")
        if self.format in {OutputResponseFormat.PLAIN_TEXT, OutputResponseFormat.MARKDOWN} and self.json_required_fields:
            raise PromptContractError("`json_required_fields` are only valid for JSON formats.")

        object.__setattr__(self, "json_schema", None if self.json_schema is None else _to_frozen_mapping(self.json_schema))
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class OutputPromptConstraints:
    """Structured instructions injectable into final prompt construction."""

    format: OutputResponseFormat
    instruction_lines: tuple[str, ...]
    refusal_lines: tuple[str, ...]
    style_lines: tuple[str, ...]
    compliance_lines: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.instruction_lines:
            raise PromptContractError("`instruction_lines` cannot be empty.")
        object.__setattr__(
            self, "instruction_lines", tuple(_validate_non_empty(item, "instruction_lines[]") for item in self.instruction_lines)
        )
        object.__setattr__(self, "refusal_lines", tuple(_validate_non_empty(item, "refusal_lines[]") for item in self.refusal_lines))
        object.__setattr__(self, "style_lines", tuple(_validate_non_empty(item, "style_lines[]") for item in self.style_lines))
        object.__setattr__(
            self, "compliance_lines", tuple(_validate_non_empty(item, "compliance_lines[]") for item in self.compliance_lines)
        )
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


class OutputContractEngine:
    """Deterministic engine for output contract instruction generation."""

    def build_constraints(self, request: OutputContractRequest) -> OutputPromptConstraints:
        format_lines = list(self._format_lines(request))
        style_lines = list(self._style_lines(request.style_profile))
        compliance_lines = list(self._compliance_lines(request.style_profile))
        refusal_lines = list(self._refusal_lines(request.refusal_policy, request.format))

        return OutputPromptConstraints(
            format=request.format,
            instruction_lines=tuple(format_lines),
            refusal_lines=tuple(refusal_lines),
            style_lines=tuple(style_lines),
            compliance_lines=tuple(compliance_lines),
            metadata={
                "format": request.format.value,
                "language": request.style_profile.language,
                "has_schema": request.json_schema is not None,
                "required_json_fields_count": len(request.json_required_fields),
            },
        )

    def _format_lines(self, request: OutputContractRequest) -> tuple[str, ...]:
        if request.format is OutputResponseFormat.PLAIN_TEXT:
            return ("Return plain text only.", "Do not use markdown syntax or JSON wrappers.")
        if request.format is OutputResponseFormat.MARKDOWN:
            return ("Return markdown content.", "Use concise headings and bullet points when helpful.")
        if request.format is OutputResponseFormat.JSON:
            lines = ["Return a single valid JSON object.", "Do not wrap JSON in markdown code fences."]
            if request.json_required_fields:
                required = ", ".join(request.json_required_fields)
                lines.append(f"Include required fields: {required}.")
            return tuple(lines)

        schema_text = json.dumps(dict(request.json_schema or {}), sort_keys=True, separators=(",", ":"))
        return (
            "Return a single valid JSON object that conforms to the provided JSON schema.",
            "Do not wrap JSON in markdown code fences.",
            f"JSON schema: {schema_text}",
        )

    def _style_lines(self, style: OutputStyleProfile) -> tuple[str, ...]:
        lines: list[str] = [f"Respond in language: {style.language}."]
        if style.style:
            lines.append(f"Use style: {style.style}.")
        if style.tone:
            lines.append(f"Use tone: {style.tone}.")
        if style.max_response_chars is not None:
            lines.append(f"Keep the response within {style.max_response_chars} characters.")
        return tuple(lines)

    def _compliance_lines(self, style: OutputStyleProfile) -> tuple[str, ...]:
        if not style.compliance_constraints:
            return ("Follow all applicable safety and policy constraints.",)
        lines = ["Follow these compliance constraints strictly:"]
        lines.extend(f"- {item}" for item in style.compliance_constraints)
        return tuple(lines)

    def _refusal_lines(
        self, policy: OutputRefusalPolicy, format_type: OutputResponseFormat
    ) -> tuple[str, ...]:
        lines: list[str] = []
        if policy.allow_refusal:
            default_refusal = "If the request is unsafe or unsupported, provide a brief refusal."
            lines.append(policy.custom_refusal_line or default_refusal)
        if policy.allow_deferral:
            default_deferral = "If you cannot complete the task reliably, defer and ask for clarifying input."
            lines.append(policy.custom_deferral_line or default_deferral)

        if format_type in {OutputResponseFormat.JSON, OutputResponseFormat.JSON_SCHEMA}:
            lines.append(
                "For refusal/deferral in JSON output, include explicit fields: "
                "`status`, `reason`, and `next_step`."
            )

        if policy.preferred_pattern is RefusalPattern.DIRECT_REFUSAL:
            lines.append("Prefer direct refusal over deferral when both are allowed.")
        else:
            lines.append("Prefer safe deferral with clear next steps when both are allowed.")
        return tuple(lines)

