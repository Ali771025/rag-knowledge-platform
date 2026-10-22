"""Template registry foundation for reusable versioned prompt templates."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Protocol

from app.prompt_orchestration.exceptions import PromptContractError
from app.prompt_orchestration.models import OutputContract, PromptMessage, PromptRole, PromptTemplate, TemplateRef
from app.prompt_orchestration.strategies import PromptStrategyType

_SEMVER_PATTERN = re.compile(r"^\d+(?:\.\d+){0,2}$")


def _validate_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise PromptContractError(f"`{field_name}` must be a non-empty string.")
    return normalized


def _normalize_language(language: str) -> str:
    return _validate_non_empty(language, "language").lower()


def _normalize_environment(environment: str) -> str:
    return _validate_non_empty(environment, "environment").lower()


def _to_frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _version_key(version: str) -> tuple[int, ...] | tuple[int, int, int, str]:
    normalized = _validate_non_empty(version, "version")
    if _SEMVER_PATTERN.match(normalized):
        parts = tuple(int(part) for part in normalized.split("."))
        return parts + (0,) * (3 - len(parts))
    return (-1, -1, -1, normalized)


class TemplateEnvironment(StrEnum):
    """Supported template environments."""

    DEFAULT = "default"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class PromptTemplateKey:
    """Lookup key for an immutable template variant."""

    strategy: PromptStrategyType
    language: str
    version: str
    environment: str = TemplateEnvironment.DEFAULT

    def __post_init__(self) -> None:
        object.__setattr__(self, "language", _normalize_language(self.language))
        object.__setattr__(self, "version", _validate_non_empty(self.version, "version"))
        object.__setattr__(self, "environment", _normalize_environment(self.environment))


@dataclass(frozen=True, slots=True)
class RegisteredPromptTemplate:
    """Registry record for one concrete template variant."""

    key: PromptTemplateKey
    template: PromptTemplate
    parent_template: TemplateRef | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.template.ref.version != self.key.version:
            raise PromptContractError("`template.ref.version` must match `RegisteredPromptTemplate.key.version`.")
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class TemplateLookupRequest:
    """Typed lookup request for retrieving a template variant."""

    strategy: PromptStrategyType
    language: str
    version: str | None = None
    environment: str = TemplateEnvironment.DEFAULT
    allow_fallback: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "language", _normalize_language(self.language))
        object.__setattr__(self, "environment", _normalize_environment(self.environment))
        if self.version is not None:
            object.__setattr__(self, "version", _validate_non_empty(self.version, "version"))


@dataclass(frozen=True, slots=True)
class TemplateLookupResult:
    """Lookup result that keeps traceability of fallback behavior."""

    record: RegisteredPromptTemplate
    requested: TemplateLookupRequest
    matched_key: PromptTemplateKey
    fallback_used: bool


class PromptTemplateLoader(Protocol):
    """Loader interface for supplying template records from any source."""

    def load_templates(self) -> Iterable[RegisteredPromptTemplate]:
        """Return registered prompt templates."""


class BasePromptTemplateLoader(ABC):
    """Abstract base class for concrete template loaders."""

    @abstractmethod
    def load_templates(self) -> Iterable[RegisteredPromptTemplate]:
        """Return registered prompt templates."""


class PromptTemplateRegistry:
    """In-memory registry for reusable, versioned, multilingual templates."""

    def __init__(
        self,
        templates: Iterable[RegisteredPromptTemplate] = (),
        loaders: Iterable[PromptTemplateLoader] = (),
        default_language: str = "en",
        default_environment: str = TemplateEnvironment.DEFAULT,
    ) -> None:
        self._records: dict[PromptTemplateKey, RegisteredPromptTemplate] = {}
        self.default_language = _normalize_language(default_language)
        self.default_environment = _normalize_environment(default_environment)

        for item in templates:
            self.register(item)
        for loader in loaders:
            self.load_from(loader)

    def register(self, record: RegisteredPromptTemplate) -> None:
        """Register one template record."""
        if record.key in self._records:
            raise PromptContractError(f"Duplicate template key: {record.key}")
        self._records[record.key] = record

    def register_many(self, records: Iterable[RegisteredPromptTemplate]) -> None:
        """Register multiple template records."""
        for record in records:
            self.register(record)

    def load_from(self, loader: PromptTemplateLoader) -> None:
        """Load template records via a loader abstraction."""
        self.register_many(loader.load_templates())

    def lookup(self, request: TemplateLookupRequest) -> TemplateLookupResult:
        """Lookup with exact match first and deterministic fallbacks."""
        match = self._lookup_exact(request)
        if match is not None:
            return TemplateLookupResult(
                record=match,
                requested=request,
                matched_key=match.key,
                fallback_used=False,
            )

        if request.allow_fallback:
            fallback = self._lookup_with_fallback(request)
            if fallback is not None:
                return TemplateLookupResult(
                    record=fallback,
                    requested=request,
                    matched_key=fallback.key,
                    fallback_used=True,
                )

        raise PromptContractError(
            "No template found for "
            f"strategy={request.strategy.value}, language={request.language}, "
            f"version={request.version or '<latest>'}, environment={request.environment}."
        )

    def list_for_strategy(self, strategy: PromptStrategyType) -> tuple[RegisteredPromptTemplate, ...]:
        """Return all templates for a strategy ordered by version descending."""
        records = [record for record in self._records.values() if record.key.strategy is strategy]
        records.sort(key=lambda record: _version_key(record.key.version), reverse=True)
        return tuple(records)

    def _lookup_exact(self, request: TemplateLookupRequest) -> RegisteredPromptTemplate | None:
        if request.version is None:
            return self._latest_for(
                strategy=request.strategy,
                language=request.language,
                environment=request.environment,
            )

        key = PromptTemplateKey(
            strategy=request.strategy,
            language=request.language,
            version=request.version,
            environment=request.environment,
        )
        return self._records.get(key)

    def _lookup_with_fallback(self, request: TemplateLookupRequest) -> RegisteredPromptTemplate | None:
        language_candidates = (request.language, self.default_language)
        environment_candidates = (request.environment, self.default_environment)

        for language in language_candidates:
            for environment in environment_candidates:
                if request.version is None:
                    candidate = self._latest_for(
                        strategy=request.strategy,
                        language=language,
                        environment=environment,
                    )
                    if candidate is not None:
                        return candidate
                    continue

                key = PromptTemplateKey(
                    strategy=request.strategy,
                    language=language,
                    version=request.version,
                    environment=environment,
                )
                candidate = self._records.get(key)
                if candidate is not None:
                    return candidate
        return None

    def _latest_for(
        self,
        *,
        strategy: PromptStrategyType,
        language: str,
        environment: str,
    ) -> RegisteredPromptTemplate | None:
        candidates = [
            record
            for record in self._records.values()
            if record.key.strategy is strategy
            and record.key.language == language
            and record.key.environment == environment
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda record: _version_key(record.key.version), reverse=True)
        return candidates[0]

    @classmethod
    def with_representative_templates(cls) -> PromptTemplateRegistry:
        """Build a registry with small representative templates."""
        return cls(templates=build_representative_templates())


def build_representative_templates() -> tuple[RegisteredPromptTemplate, ...]:
    """Small starter templates for each supported strategy."""

    strategy_prompts = {
        PromptStrategyType.ONBOARDING_GUIDANCE: "Guide the user through onboarding with concise steps.",
        PromptStrategyType.RAG_ANSWER: "Answer using provided context and cite sources when available.",
        PromptStrategyType.CLARIFICATION: "Ask a focused clarifying question before proceeding.",
        PromptStrategyType.NEXT_BEST_STEP: "Recommend the next most useful action and explain why.",
        PromptStrategyType.TROUBLESHOOTING: "Diagnose the issue using observable facts and propose fixes.",
        PromptStrategyType.SUMMARIZATION: "Summarize the context in key points and action items.",
        PromptStrategyType.CONTINUATION: "Continue the conversation while preserving prior intent.",
    }

    templates: list[RegisteredPromptTemplate] = []
    for strategy, system_prompt in strategy_prompts.items():
        version = "1.0.0"
        template_id = f"{strategy.value}.base"
        template = PromptTemplate(
            ref=TemplateRef(template_id=template_id, version=version),
            instruction_messages=(PromptMessage(role=PromptRole.SYSTEM, content=system_prompt),),
            input_variables=frozenset({"user_input"}),
            default_output_contract=OutputContract(),
            metadata={"strategy": strategy.value, "language": "en"},
        )
        templates.append(
            RegisteredPromptTemplate(
                key=PromptTemplateKey(
                    strategy=strategy,
                    language="en",
                    version=version,
                    environment=TemplateEnvironment.DEFAULT,
                ),
                template=template,
            )
        )

    # Extra variant to demonstrate multilingual fallback behavior.
    templates.append(
        RegisteredPromptTemplate(
            key=PromptTemplateKey(
                strategy=PromptStrategyType.ONBOARDING_GUIDANCE,
                language="es",
                version="1.0.0",
                environment=TemplateEnvironment.DEFAULT,
            ),
            template=PromptTemplate(
                ref=TemplateRef(template_id="onboarding_guidance.base.es", version="1.0.0"),
                instruction_messages=(
                    PromptMessage(
                        role=PromptRole.SYSTEM,
                        content="Guia al usuario en el onboarding con pasos claros y cortos.",
                    ),
                ),
                input_variables=frozenset({"user_input"}),
                default_output_contract=OutputContract(),
                metadata={"strategy": PromptStrategyType.ONBOARDING_GUIDANCE.value, "language": "es"},
            ),
            parent_template=TemplateRef(template_id="onboarding_guidance.base", version="1.0.0"),
        )
    )

    return tuple(templates)
