"""Internal service-to-service interface for prompt orchestration.

This facade provides thin DTO mapping and delegates orchestration behavior to
PromptOrchestrationService.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID

from app.prompt_orchestration.context_models import (
    AuthoritativeContext,
    ConstraintStrength,
    ConversationalContext,
    MemorySummary,
    PersonalizationContext,
    PolicyConstraint,
    PromptContextEnvelope,
    RecentMessage,
    RetrievedChunk,
    ToolResult,
    ToolResultStatus,
    UserProfileSnapshot,
)
from app.prompt_orchestration.exceptions import PromptContractError
from app.prompt_orchestration.models import PromptMessage, PromptOrchestrationRequest, PromptRole
from app.prompt_orchestration.config import PromptOrchestrationConfig
from app.prompt_orchestration.observability import PromptTraceMetadata
from app.prompt_orchestration.service import PromptOrchestrationRequestEnvelope, PromptOrchestrationService


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


def _coerce_uuid(value: UUID | str | None, field_name: str) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise PromptContractError(f"Invalid UUID for `{field_name}`.") from exc


@dataclass(frozen=True, slots=True)
class InternalPromptMessageDTO:
    """Internal DTO for prompt messages."""

    role: str
    content: str
    name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _validate_non_empty(self.role, "role").lower())
        object.__setattr__(self, "content", _validate_non_empty(self.content, "content"))
        object.__setattr__(self, "name", _validate_optional_non_empty(self.name, "name"))


@dataclass(frozen=True, slots=True)
class InternalRetrievedChunkDTO:
    """Internal DTO for authoritative retrieved chunks."""

    chunk_id: str
    source_id: str
    content: str
    relevance_score: float
    citation: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "chunk_id", _validate_non_empty(self.chunk_id, "chunk_id"))
        object.__setattr__(self, "source_id", _validate_non_empty(self.source_id, "source_id"))
        object.__setattr__(self, "content", _validate_non_empty(self.content, "content"))
        object.__setattr__(self, "citation", _validate_optional_non_empty(self.citation, "citation"))
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class InternalPolicyConstraintDTO:
    """Internal DTO for policy constraints."""

    constraint_id: str
    instruction: str
    strength: str = "hard"
    source: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "constraint_id", _validate_non_empty(self.constraint_id, "constraint_id"))
        object.__setattr__(self, "instruction", _validate_non_empty(self.instruction, "instruction"))
        object.__setattr__(self, "strength", _validate_non_empty(self.strength, "strength").lower())
        object.__setattr__(self, "source", _validate_optional_non_empty(self.source, "source"))


@dataclass(frozen=True, slots=True)
class InternalToolResultDTO:
    """Internal DTO for tool result context."""

    tool_name: str
    status: str
    summary: str
    output_payload: Mapping[str, Any] = field(default_factory=dict)
    error_message: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "tool_name", _validate_non_empty(self.tool_name, "tool_name"))
        object.__setattr__(self, "status", _validate_non_empty(self.status, "status").lower())
        object.__setattr__(self, "summary", _validate_non_empty(self.summary, "summary"))
        object.__setattr__(self, "error_message", _validate_optional_non_empty(self.error_message, "error_message"))
        object.__setattr__(self, "output_payload", _to_frozen_mapping(self.output_payload))


@dataclass(frozen=True, slots=True)
class InternalPromptContextDTO:
    """Internal context DTO for orchestration requests."""

    retrieved_chunks: tuple[InternalRetrievedChunkDTO, ...] = ()
    conversation_history: tuple[InternalPromptMessageDTO, ...] = ()
    memory_summary: str | None = None
    user_profile: Mapping[str, Any] = field(default_factory=dict)
    policy_constraints: tuple[InternalPolicyConstraintDTO, ...] = ()
    tool_results: tuple[InternalToolResultDTO, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "memory_summary", _validate_optional_non_empty(self.memory_summary, "memory_summary"))
        object.__setattr__(self, "user_profile", _to_frozen_mapping(self.user_profile))


@dataclass(frozen=True, slots=True)
class InternalPromptOrchestrationRequestDTO:
    """Internal request DTO used by backend services."""

    request_id: str
    user_input: str
    session_id: UUID | str | None = None
    user_id: UUID | str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    template_variables: Mapping[str, Any] = field(default_factory=dict)
    context: InternalPromptContextDTO = field(default_factory=InternalPromptContextDTO)
    trace: PromptTraceMetadata = field(default_factory=PromptTraceMetadata)

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _validate_non_empty(self.request_id, "request_id"))
        object.__setattr__(self, "user_input", _validate_non_empty(self.user_input, "user_input"))
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))
        object.__setattr__(self, "template_variables", _to_frozen_mapping(self.template_variables))


@dataclass(frozen=True, slots=True)
class InternalPromptOrchestrationResponseDTO:
    """Internal response DTO returned to backend callers."""

    request_id: str
    template_id: str
    template_version: str
    messages: tuple[InternalPromptMessageDTO, ...]
    output_format: str
    grounding_mode: str
    warnings: tuple[str, ...] = ()
    trace: PromptTraceMetadata = field(default_factory=PromptTraceMetadata)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _validate_non_empty(self.request_id, "request_id"))
        object.__setattr__(self, "template_id", _validate_non_empty(self.template_id, "template_id"))
        object.__setattr__(self, "template_version", _validate_non_empty(self.template_version, "template_version"))
        object.__setattr__(self, "output_format", _validate_non_empty(self.output_format, "output_format"))
        object.__setattr__(self, "grounding_mode", _validate_non_empty(self.grounding_mode, "grounding_mode"))
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


class PromptOrchestrationInternalFacade:
    """Thin internal facade for service-to-service prompt orchestration calls."""

    def __init__(
        self,
        service: PromptOrchestrationService | None = None,
        *,
        config: PromptOrchestrationConfig | None = None,
    ) -> None:
        self._service = service or PromptOrchestrationService.default(config=config)

    def build_prompt(self, request: InternalPromptOrchestrationRequestDTO) -> InternalPromptOrchestrationResponseDTO:
        envelope = self._map_request(request)
        result = self._service.orchestrate(envelope)
        return InternalPromptOrchestrationResponseDTO(
            request_id=result.request_id,
            template_id=result.template_ref.template_id,
            template_version=result.template_ref.version,
            messages=tuple(self._to_message_dto(item) for item in result.messages),
            output_format=result.output_contract.format.value,
            grounding_mode=result.grounding_policy.mode.value,
            warnings=result.audit_record.warnings,
            trace=request.trace,
            metadata={
                "resolved_variables": list(result.audit_record.resolved_variables),
                "unresolved_variables": list(result.audit_record.unresolved_variables),
                "created_at": result.audit_record.created_at.isoformat(),
            },
        )

    def _map_request(self, request: InternalPromptOrchestrationRequestDTO) -> PromptOrchestrationRequestEnvelope:
        session_id = _coerce_uuid(request.session_id, "session_id")
        user_id = _coerce_uuid(request.user_id, "user_id")

        domain_request = PromptOrchestrationRequest(
            session_id=session_id,
            user_id=user_id,
            request_id=request.request_id,
            user_input=request.user_input,
            metadata=request.metadata,
        )

        context = self._map_context(request.context, user_id=user_id)
        return PromptOrchestrationRequestEnvelope(
            request=domain_request,
            context=context,
            template_variables=request.template_variables,
            trace_metadata=request.trace,
        )

    def _map_context(self, dto: InternalPromptContextDTO, *, user_id: UUID | None) -> PromptContextEnvelope:
        retrieved_chunks = tuple(
            RetrievedChunk(
                chunk_id=item.chunk_id,
                source_id=item.source_id,
                content=item.content,
                relevance_score=item.relevance_score,
                citation=item.citation,
                metadata=item.metadata,
            )
            for item in dto.retrieved_chunks
        )

        policy_constraints = tuple(
            PolicyConstraint(
                constraint_id=item.constraint_id,
                instruction=item.instruction,
                strength=ConstraintStrength(item.strength),
                source=item.source,
            )
            for item in dto.policy_constraints
        )

        tool_results = tuple(
            ToolResult(
                tool_name=item.tool_name,
                status=ToolResultStatus(item.status),
                summary=item.summary,
                output_payload=item.output_payload,
                error_message=item.error_message,
            )
            for item in dto.tool_results
        )

        recent_messages = tuple(
            RecentMessage(
                message=PromptMessage(
                    role=PromptRole(item.role),
                    content=item.content,
                    name=item.name,
                ),
                occurred_at=datetime.now(UTC),
            )
            for item in dto.conversation_history
        )

        memory_summary = None
        if dto.memory_summary:
            memory_summary = MemorySummary(summary=dto.memory_summary)

        user_profile = None
        if dto.user_profile:
            preferred_language = self._coerce_optional_str(dto.user_profile.get("preferred_language"))
            tone_preference = self._coerce_optional_str(dto.user_profile.get("tone_preference"))
            expertise_level = self._coerce_optional_str(dto.user_profile.get("expertise_level"))
            preferences = {
                key: value
                for key, value in dto.user_profile.items()
                if key not in {"preferred_language", "tone_preference", "expertise_level"}
            }
            user_profile = UserProfileSnapshot(
                user_id=user_id,
                preferred_language=preferred_language,
                tone_preference=tone_preference,
                expertise_level=expertise_level,
                preferences=preferences,
            )

        return PromptContextEnvelope(
            authoritative=AuthoritativeContext(
                retrieved_chunks=retrieved_chunks,
                policy_constraints=policy_constraints,
                tool_results=tool_results,
            ),
            conversational=ConversationalContext(
                memory_summary=memory_summary,
                recent_messages=recent_messages,
            ),
            personalization=PersonalizationContext(user_profile=user_profile),
        )

    def _to_message_dto(self, message: PromptMessage) -> InternalPromptMessageDTO:
        return InternalPromptMessageDTO(
            role=message.role.value,
            content=message.content,
            name=message.name,
        )

    def _coerce_optional_str(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
