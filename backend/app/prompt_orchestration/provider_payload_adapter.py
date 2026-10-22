"""Provider payload adapters for prompt-orchestration outputs.

This module converts internal prompt-build results into transport-ready payloads
without performing provider HTTP calls.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Generic, Mapping, TypeVar

from app.prompt_orchestration.exceptions import PromptContractError
from app.prompt_orchestration.models import OutputFormat, PromptBuildResult


PayloadT = TypeVar("PayloadT")


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


class InferenceMessageRole(StrEnum):
    """Provider-agnostic message role labels."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ProviderPayloadKind(StrEnum):
    """Kinds of inference payloads emitted by adapters."""

    GENERIC_CHAT = "generic_chat"
    OPENAI_CHAT_COMPLETIONS = "openai_chat_completions"


@dataclass(frozen=True, slots=True)
class InferenceMessagePayload:
    """Provider-agnostic representation of an inference message."""

    role: InferenceMessageRole
    content: str
    name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "content", _validate_non_empty(self.content, "content"))
        object.__setattr__(self, "name", _validate_optional_non_empty(self.name, "name"))


@dataclass(frozen=True, slots=True)
class ProviderPayload:
    """Provider-agnostic inference payload abstraction."""

    kind: ProviderPayloadKind
    request_id: str
    messages: tuple[InferenceMessagePayload, ...]
    model_hint: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    response_format_hint: Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _validate_non_empty(self.request_id, "request_id"))
        if not self.messages:
            raise PromptContractError("`messages` cannot be empty.")

        object.__setattr__(self, "model_hint", _validate_optional_non_empty(self.model_hint, "model_hint"))
        if self.temperature is not None and (self.temperature < 0 or self.temperature > 2):
            raise PromptContractError("`temperature` must be between 0 and 2.")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise PromptContractError("`max_tokens` must be greater than zero when provided.")

        hint = None if self.response_format_hint is None else _to_frozen_mapping(self.response_format_hint)
        object.__setattr__(self, "response_format_hint", hint)
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ProviderPayloadAdapterRequest:
    """Input for payload adapter execution."""

    prompt: PromptBuildResult
    model_hint: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_hint", _validate_optional_non_empty(self.model_hint, "model_hint"))
        if self.temperature is not None and (self.temperature < 0 or self.temperature > 2):
            raise PromptContractError("`temperature` must be between 0 and 2.")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise PromptContractError("`max_tokens` must be greater than zero when provided.")
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


class ProviderPayloadAdapter(ABC, Generic[PayloadT]):
    """Base adapter for converting prompt results into provider payloads."""

    @abstractmethod
    def adapt(self, request: ProviderPayloadAdapterRequest) -> PayloadT:
        """Convert a prompt build result into a transport-ready payload."""


class GenericProviderPayloadAdapter(ProviderPayloadAdapter[ProviderPayload]):
    """Adapter that emits provider-agnostic payloads for generic chat transports."""

    def adapt(self, request: ProviderPayloadAdapterRequest) -> ProviderPayload:
        message_payloads = tuple(
            InferenceMessagePayload(
                role=InferenceMessageRole(message.role.value),
                content=message.content,
                name=message.name,
            )
            for message in request.prompt.messages
        )

        return ProviderPayload(
            kind=ProviderPayloadKind.GENERIC_CHAT,
            request_id=request.prompt.request_id,
            messages=message_payloads,
            model_hint=request.model_hint,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            response_format_hint=self._response_format_hint(request.prompt),
            metadata={
                "template_id": request.prompt.template_ref.template_id,
                "template_version": request.prompt.template_ref.version,
                **dict(request.metadata),
            },
        )

    def _response_format_hint(self, prompt: PromptBuildResult) -> Mapping[str, Any]:
        contract = prompt.output_contract
        if contract.format is OutputFormat.TEXT:
            return {"type": "text"}
        if contract.format is OutputFormat.JSON_OBJECT:
            return {"type": "json_object"}

        return {
            "type": "json_schema",
            "schema": dict(contract.json_schema or {}),
        }


class OpenAIChatCompletionsPayloadAdapter(ProviderPayloadAdapter[Mapping[str, Any]]):
    """Example provider-shaped adapter for OpenAI-style chat completions payloads."""

    def __init__(self, *, default_model: str = "gpt-4.1-mini") -> None:
        self._default_model = _validate_non_empty(default_model, "default_model")
        self._generic = GenericProviderPayloadAdapter()

    def adapt(self, request: ProviderPayloadAdapterRequest) -> Mapping[str, Any]:
        generic_payload = self._generic.adapt(request)

        payload: dict[str, Any] = {
            "model": generic_payload.model_hint or self._default_model,
            "messages": [
                {
                    key: value
                    for key, value in {
                        "role": message.role.value,
                        "content": message.content,
                        "name": message.name,
                    }.items()
                    if value is not None
                }
                for message in generic_payload.messages
            ],
            "metadata": dict(generic_payload.metadata),
        }

        if generic_payload.temperature is not None:
            payload["temperature"] = generic_payload.temperature
        if generic_payload.max_tokens is not None:
            payload["max_tokens"] = generic_payload.max_tokens

        response_format = generic_payload.response_format_hint or {"type": "text"}
        if response_format.get("type") == "json_object":
            payload["response_format"] = {"type": "json_object"}
        elif response_format.get("type") == "json_schema":
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "prompt_orchestration_response",
                    "schema": dict(response_format.get("schema", {})),
                },
            }

        return MappingProxyType(payload)
