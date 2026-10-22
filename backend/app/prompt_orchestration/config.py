"""Environment-aware typed configuration for prompt orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from types import MappingProxyType
from typing import Any, Mapping

from app.prompt_orchestration.context_assembler import ContextAssemblyLimits
from app.prompt_orchestration.exceptions import PromptContractError
from app.prompt_orchestration.grounding_policy_engine import GroundingPolicyMode, InsufficientContextPolicy
from app.prompt_orchestration.strategies import PromptStrategyType


def _validate_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise PromptContractError(f"`{field_name}` must be a non-empty string.")
    return normalized


def _to_frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _env_bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    value = env.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise PromptContractError(f"Invalid boolean for env var `{name}`: {value}")


def _env_int(env: Mapping[str, str], name: str, default: int) -> int:
    value = env.get(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except (TypeError, ValueError) as exc:
        raise PromptContractError(f"Invalid integer for env var `{name}`: {value}") from exc


@dataclass(frozen=True, slots=True)
class PromptTemplateDefaultsConfig:
    """Template selection defaults."""

    default_versions: Mapping[PromptStrategyType, str] = field(default_factory=dict)
    default_language: str = "en"

    def __post_init__(self) -> None:
        object.__setattr__(self, "default_language", _validate_non_empty(self.default_language, "default_language").lower())

        normalized: dict[PromptStrategyType, str] = {}
        for key, value in self.default_versions.items():
            strategy = key if isinstance(key, PromptStrategyType) else PromptStrategyType(str(key))
            normalized[strategy] = _validate_non_empty(str(value), "default_versions[]")
        object.__setattr__(self, "default_versions", _to_frozen_mapping(normalized))


@dataclass(frozen=True, slots=True)
class PromptGroundingDefaultsConfig:
    """Grounding policy defaults used when request metadata omits explicit values."""

    default_mode: GroundingPolicyMode = GroundingPolicyMode.GROUNDED_PREFERRED
    default_insufficient_context_policy: InsufficientContextPolicy = InsufficientContextPolicy.ASK_CLARIFYING_QUESTION


@dataclass(frozen=True, slots=True)
class PromptContextBudgetsConfig:
    """Typed context budget configuration."""

    max_authoritative_chunks: int = 8
    max_authoritative_chars: int = 5000
    max_conversational_messages: int = 8
    max_conversational_chars: int = 2500
    max_personalization_entries: int = 12
    max_operational_constraints: int = 8
    max_operational_chars: int = 2500
    max_total_chars: int = 9000

    def to_limits(self) -> ContextAssemblyLimits:
        return ContextAssemblyLimits(
            max_authoritative_chunks=self.max_authoritative_chunks,
            max_authoritative_chars=self.max_authoritative_chars,
            max_conversational_messages=self.max_conversational_messages,
            max_conversational_chars=self.max_conversational_chars,
            max_personalization_entries=self.max_personalization_entries,
            max_operational_constraints=self.max_operational_constraints,
            max_operational_chars=self.max_operational_chars,
            max_total_chars=self.max_total_chars,
        )


@dataclass(frozen=True, slots=True)
class PromptLanguageConfig:
    """Language defaults for prompt orchestration."""

    default_language: str = "en"

    def __post_init__(self) -> None:
        object.__setattr__(self, "default_language", _validate_non_empty(self.default_language, "default_language").lower())


@dataclass(frozen=True, slots=True)
class PromptObservabilityConfig:
    """Observability behavior for prompt orchestration."""

    metrics_enabled: bool = True
    audit_enabled: bool = True
    metrics_logger_name: str = "app.prompt_orchestration.metrics"
    audit_logger_name: str = "app.prompt_orchestration.audit"
    audit_preview_chars: int = 160

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics_logger_name", _validate_non_empty(self.metrics_logger_name, "metrics_logger_name"))
        object.__setattr__(self, "audit_logger_name", _validate_non_empty(self.audit_logger_name, "audit_logger_name"))
        if self.audit_preview_chars <= 0:
            raise PromptContractError("`audit_preview_chars` must be greater than zero.")


@dataclass(frozen=True, slots=True)
class PromptOrchestrationConfig:
    """Root config object for prompt orchestration module wiring."""

    environment: str = "development"
    templates: PromptTemplateDefaultsConfig = field(default_factory=PromptTemplateDefaultsConfig)
    grounding: PromptGroundingDefaultsConfig = field(default_factory=PromptGroundingDefaultsConfig)
    context_budgets: PromptContextBudgetsConfig = field(default_factory=PromptContextBudgetsConfig)
    language: PromptLanguageConfig = field(default_factory=PromptLanguageConfig)
    observability: PromptObservabilityConfig = field(default_factory=PromptObservabilityConfig)

    def __post_init__(self) -> None:
        object.__setattr__(self, "environment", _validate_non_empty(self.environment, "environment").lower())

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> PromptOrchestrationConfig:
        source = env or os.environ
        environment = source.get("PROMPT_ORCH_ENV", "development")

        default_language = source.get("PROMPT_ORCH_DEFAULT_LANGUAGE", "en")
        template_defaults = PromptTemplateDefaultsConfig(
            default_versions=_parse_default_versions(source.get("PROMPT_ORCH_DEFAULT_TEMPLATE_VERSIONS")),
            default_language=default_language,
        )

        grounding_mode_raw = source.get("PROMPT_ORCH_DEFAULT_GROUNDING_MODE", GroundingPolicyMode.GROUNDED_PREFERRED.value)
        insufficient_raw = source.get(
            "PROMPT_ORCH_DEFAULT_INSUFFICIENT_CONTEXT_POLICY",
            InsufficientContextPolicy.ASK_CLARIFYING_QUESTION.value,
        )
        grounding = PromptGroundingDefaultsConfig(
            default_mode=GroundingPolicyMode(str(grounding_mode_raw).strip().lower()),
            default_insufficient_context_policy=InsufficientContextPolicy(str(insufficient_raw).strip().lower()),
        )

        budgets = PromptContextBudgetsConfig(
            max_authoritative_chunks=_env_int(source, "PROMPT_ORCH_MAX_AUTHORITATIVE_CHUNKS", 8),
            max_authoritative_chars=_env_int(source, "PROMPT_ORCH_MAX_AUTHORITATIVE_CHARS", 5000),
            max_conversational_messages=_env_int(source, "PROMPT_ORCH_MAX_CONVERSATIONAL_MESSAGES", 8),
            max_conversational_chars=_env_int(source, "PROMPT_ORCH_MAX_CONVERSATIONAL_CHARS", 2500),
            max_personalization_entries=_env_int(source, "PROMPT_ORCH_MAX_PERSONALIZATION_ENTRIES", 12),
            max_operational_constraints=_env_int(source, "PROMPT_ORCH_MAX_OPERATIONAL_CONSTRAINTS", 8),
            max_operational_chars=_env_int(source, "PROMPT_ORCH_MAX_OPERATIONAL_CHARS", 2500),
            max_total_chars=_env_int(source, "PROMPT_ORCH_MAX_TOTAL_CHARS", 9000),
        )

        observability = PromptObservabilityConfig(
            metrics_enabled=_env_bool(source, "PROMPT_ORCH_METRICS_ENABLED", True),
            audit_enabled=_env_bool(source, "PROMPT_ORCH_AUDIT_ENABLED", True),
            metrics_logger_name=source.get("PROMPT_ORCH_METRICS_LOGGER", "app.prompt_orchestration.metrics"),
            audit_logger_name=source.get("PROMPT_ORCH_AUDIT_LOGGER", "app.prompt_orchestration.audit"),
            audit_preview_chars=_env_int(source, "PROMPT_ORCH_AUDIT_PREVIEW_CHARS", 160),
        )

        return cls(
            environment=environment,
            templates=template_defaults,
            grounding=grounding,
            context_budgets=budgets,
            language=PromptLanguageConfig(default_language=default_language),
            observability=observability,
        )


def _parse_default_versions(value: str | None) -> Mapping[PromptStrategyType, str]:
    if value is None:
        return {}

    text = value.strip()
    if not text:
        return {}

    items = [item.strip() for item in text.split(",") if item.strip()]
    parsed: dict[PromptStrategyType, str] = {}
    for item in items:
        if ":" not in item:
            raise PromptContractError(
                "Invalid `PROMPT_ORCH_DEFAULT_TEMPLATE_VERSIONS` entry; expected `strategy:version` pairs."
            )
        strategy_raw, version_raw = item.split(":", 1)
        strategy = PromptStrategyType(strategy_raw.strip().lower())
        version = _validate_non_empty(version_raw, "default_versions.version")
        parsed[strategy] = version
    return parsed
