"""Observability and safe auditing for prompt orchestration.

This module provides pluggable metrics hooks and redacted audit records.
It intentionally avoids provider transport and HTTP concerns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
import re
from types import MappingProxyType
from typing import Any, Mapping

from app.prompt_orchestration.exceptions import PromptContractError
from app.prompt_orchestration.models import PromptBuildResult, PromptMessage


logger = logging.getLogger(__name__)


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


@dataclass(frozen=True, slots=True)
class PromptTraceMetadata:
    """Correlation and trace metadata for prompt orchestration executions."""

    trace_id: str | None = None
    correlation_id: str | None = None
    span_id: str | None = None
    source_service: str | None = None
    tags: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "trace_id", _validate_optional_non_empty(self.trace_id, "trace_id"))
        object.__setattr__(self, "correlation_id", _validate_optional_non_empty(self.correlation_id, "correlation_id"))
        object.__setattr__(self, "span_id", _validate_optional_non_empty(self.span_id, "span_id"))
        object.__setattr__(self, "source_service", _validate_optional_non_empty(self.source_service, "source_service"))

        normalized_tags: dict[str, str] = {}
        for key, value in self.tags.items():
            key_norm = _validate_non_empty(str(key), "tags.key")
            value_norm = _validate_non_empty(str(value), "tags.value")
            normalized_tags[key_norm] = value_norm
        object.__setattr__(self, "tags", _to_frozen_mapping(normalized_tags))


@dataclass(frozen=True, slots=True)
class RedactionRule:
    """Pattern rule used for sensitive-content redaction."""

    name: str
    pattern: re.Pattern[str]
    replacement: str = "[REDACTED]"

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _validate_non_empty(self.name, "name"))
        object.__setattr__(self, "replacement", _validate_non_empty(self.replacement, "replacement"))


class SensitiveContentRedactor:
    """Redacts known sensitive patterns from log/audit content."""

    def __init__(self, rules: tuple[RedactionRule, ...] | None = None) -> None:
        self._rules = rules or self.default_rules()

    @staticmethod
    def default_rules() -> tuple[RedactionRule, ...]:
        return (
            RedactionRule(
                name="email",
                pattern=re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
            ),
            RedactionRule(
                name="phone",
                pattern=re.compile(r"\b(?:\+?\d{1,2}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b"),
            ),
            RedactionRule(
                name="ssn",
                pattern=re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            ),
            RedactionRule(
                name="credit_card",
                pattern=re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
            ),
            RedactionRule(
                name="bearer_token",
                pattern=re.compile(r"\bBearer\s+[A-Za-z0-9._\-+=/]+\b", re.IGNORECASE),
            ),
            RedactionRule(
                name="api_key",
                pattern=re.compile(r"\b(?:api[_-]?key|token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}['\"]?", re.IGNORECASE),
            ),
        )

    def redact_text(self, text: str) -> str:
        redacted = text
        for rule in self._rules:
            redacted = rule.pattern.sub(rule.replacement, redacted)
        return redacted


@dataclass(frozen=True, slots=True)
class SafePromptAuditRecord:
    """Audit-safe prompt build record with redacted message previews."""

    request_id: str
    template_id: str | None
    template_version: str | None
    grounding_mode: str | None
    output_format: str | None
    message_count: int
    redacted_message_previews: tuple[str, ...] = ()
    warning_count: int = 0
    resolved_variable_names: tuple[str, ...] = ()
    failure_type: str | None = None
    failure_message: str | None = None
    trace_metadata: PromptTraceMetadata = field(default_factory=PromptTraceMetadata)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _validate_non_empty(self.request_id, "request_id"))
        object.__setattr__(self, "template_id", _validate_optional_non_empty(self.template_id, "template_id"))
        object.__setattr__(self, "template_version", _validate_optional_non_empty(self.template_version, "template_version"))
        object.__setattr__(self, "grounding_mode", _validate_optional_non_empty(self.grounding_mode, "grounding_mode"))
        object.__setattr__(self, "output_format", _validate_optional_non_empty(self.output_format, "output_format"))
        object.__setattr__(self, "failure_type", _validate_optional_non_empty(self.failure_type, "failure_type"))
        object.__setattr__(self, "failure_message", _validate_optional_non_empty(self.failure_message, "failure_message"))

        if self.message_count < 0:
            raise PromptContractError("`message_count` cannot be negative.")
        if self.warning_count < 0:
            raise PromptContractError("`warning_count` cannot be negative.")
        if self.created_at.tzinfo is None:
            raise PromptContractError("`created_at` must be timezone-aware.")

        previews = tuple(_validate_non_empty(item, "redacted_message_previews[]") for item in self.redacted_message_previews)
        object.__setattr__(self, "redacted_message_previews", previews)

        variable_names = tuple(_validate_non_empty(item, "resolved_variable_names[]") for item in self.resolved_variable_names)
        object.__setattr__(self, "resolved_variable_names", variable_names)
        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


class PromptAuditRecordFactory:
    """Builds safe audit records from prompt orchestration outcomes."""

    def __init__(self, redactor: SensitiveContentRedactor | None = None, *, preview_chars: int = 160) -> None:
        if preview_chars <= 0:
            raise PromptContractError("`preview_chars` must be greater than zero.")
        self._redactor = redactor or SensitiveContentRedactor()
        self._preview_chars = preview_chars

    def build_success(
        self,
        *,
        result: PromptBuildResult,
        trace: PromptTraceMetadata,
        metadata: Mapping[str, Any] | None = None,
    ) -> SafePromptAuditRecord:
        previews = self._message_previews(result.messages)
        return SafePromptAuditRecord(
            request_id=result.request_id,
            template_id=result.template_ref.template_id,
            template_version=result.template_ref.version,
            grounding_mode=result.grounding_policy.mode.value,
            output_format=result.output_contract.format.value,
            message_count=len(result.messages),
            redacted_message_previews=previews,
            warning_count=len(result.audit_record.warnings),
            resolved_variable_names=result.audit_record.resolved_variables,
            trace_metadata=trace,
            metadata=dict(metadata or {}),
        )

    def build_failure(
        self,
        *,
        request_id: str,
        trace: PromptTraceMetadata,
        failure_type: str,
        failure_message: str,
        template_id: str | None = None,
        template_version: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> SafePromptAuditRecord:
        redacted_message = self._redactor.redact_text(failure_message)
        if len(redacted_message) > self._preview_chars:
            redacted_message = redacted_message[: self._preview_chars - 3] + "..."

        return SafePromptAuditRecord(
            request_id=request_id,
            template_id=template_id,
            template_version=template_version,
            grounding_mode=None,
            output_format=None,
            message_count=0,
            redacted_message_previews=(),
            failure_type=failure_type,
            failure_message=redacted_message,
            trace_metadata=trace,
            metadata=dict(metadata or {}),
        )

    def _message_previews(self, messages: tuple[PromptMessage, ...]) -> tuple[str, ...]:
        previews: list[str] = []
        for message in messages:
            redacted = self._redactor.redact_text(message.content)
            if len(redacted) > self._preview_chars:
                redacted = redacted[: self._preview_chars - 3] + "..."
            previews.append(f"{message.role.value}:{redacted}")
        return tuple(previews)


class PromptAuditSink(ABC):
    """Pluggable sink for safe prompt audit records."""

    @abstractmethod
    def record(self, audit_record: SafePromptAuditRecord) -> None:
        """Emit one safe prompt audit record."""


class NoOpPromptAuditSink(PromptAuditSink):
    """Default no-op audit sink."""

    def record(self, audit_record: SafePromptAuditRecord) -> None:
        _ = audit_record


class LoggingPromptAuditSink(PromptAuditSink):
    """Logging-based audit sink that emits structured safe records."""

    def __init__(self, logger_name: str = "app.prompt_orchestration.audit") -> None:
        self._logger = logging.getLogger(logger_name)

    def record(self, audit_record: SafePromptAuditRecord) -> None:
        self._logger.info(
            "prompt_audit request_id=%s template_id=%s template_version=%s failure_type=%s trace_id=%s correlation_id=%s",
            audit_record.request_id,
            audit_record.template_id,
            audit_record.template_version,
            audit_record.failure_type,
            audit_record.trace_metadata.trace_id,
            audit_record.trace_metadata.correlation_id,
            extra={
                "prompt_audit": {
                    "request_id": audit_record.request_id,
                    "template_id": audit_record.template_id,
                    "template_version": audit_record.template_version,
                    "grounding_mode": audit_record.grounding_mode,
                    "output_format": audit_record.output_format,
                    "message_count": audit_record.message_count,
                    "redacted_message_previews": list(audit_record.redacted_message_previews),
                    "warning_count": audit_record.warning_count,
                    "resolved_variable_names": list(audit_record.resolved_variable_names),
                    "failure_type": audit_record.failure_type,
                    "failure_message": audit_record.failure_message,
                    "trace_id": audit_record.trace_metadata.trace_id,
                    "correlation_id": audit_record.trace_metadata.correlation_id,
                    "span_id": audit_record.trace_metadata.span_id,
                    "source_service": audit_record.trace_metadata.source_service,
                    "trace_tags": dict(audit_record.trace_metadata.tags),
                    "metadata": dict(audit_record.metadata),
                    "created_at": audit_record.created_at.isoformat(),
                }
            },
        )


class PromptOrchestrationMetrics(ABC):
    """Pluggable metrics hooks for prompt orchestration."""

    @abstractmethod
    def prompt_build_count(self, *, tags: Mapping[str, str] | None = None) -> None:
        """Increment prompt build count."""

    @abstractmethod
    def prompt_build_latency(self, *, latency_ms: float, tags: Mapping[str, str] | None = None) -> None:
        """Observe prompt build latency."""

    @abstractmethod
    def template_usage(self, *, template_id: str, version: str, tags: Mapping[str, str] | None = None) -> None:
        """Track template usage."""

    @abstractmethod
    def grounding_mode_usage(self, *, grounding_mode: str, tags: Mapping[str, str] | None = None) -> None:
        """Track grounding mode usage."""

    @abstractmethod
    def output_contract_usage(self, *, output_format: str, tags: Mapping[str, str] | None = None) -> None:
        """Track output contract usage."""

    @abstractmethod
    def prompt_failures(self, *, error_type: str, tags: Mapping[str, str] | None = None) -> None:
        """Track prompt build failures."""


class NoOpPromptOrchestrationMetrics(PromptOrchestrationMetrics):
    """Default no-op metrics hook implementation."""

    def prompt_build_count(self, *, tags: Mapping[str, str] | None = None) -> None:
        _ = tags

    def prompt_build_latency(self, *, latency_ms: float, tags: Mapping[str, str] | None = None) -> None:
        _ = (latency_ms, tags)

    def template_usage(self, *, template_id: str, version: str, tags: Mapping[str, str] | None = None) -> None:
        _ = (template_id, version, tags)

    def grounding_mode_usage(self, *, grounding_mode: str, tags: Mapping[str, str] | None = None) -> None:
        _ = (grounding_mode, tags)

    def output_contract_usage(self, *, output_format: str, tags: Mapping[str, str] | None = None) -> None:
        _ = (output_format, tags)

    def prompt_failures(self, *, error_type: str, tags: Mapping[str, str] | None = None) -> None:
        _ = (error_type, tags)


class LoggingPromptOrchestrationMetrics(PromptOrchestrationMetrics):
    """Simple logging-backed metrics implementation for local deployments."""

    def __init__(self, logger_name: str = "app.prompt_orchestration.metrics") -> None:
        self._logger = logging.getLogger(logger_name)

    def prompt_build_count(self, *, tags: Mapping[str, str] | None = None) -> None:
        self._logger.debug("metric=prompt_build_count value=1 tags=%s", dict(tags or {}))

    def prompt_build_latency(self, *, latency_ms: float, tags: Mapping[str, str] | None = None) -> None:
        self._logger.debug("metric=prompt_build_latency value_ms=%.3f tags=%s", latency_ms, dict(tags or {}))

    def template_usage(self, *, template_id: str, version: str, tags: Mapping[str, str] | None = None) -> None:
        self._logger.debug(
            "metric=template_usage value=1 template_id=%s version=%s tags=%s",
            template_id,
            version,
            dict(tags or {}),
        )

    def grounding_mode_usage(self, *, grounding_mode: str, tags: Mapping[str, str] | None = None) -> None:
        self._logger.debug("metric=grounding_mode_usage value=1 grounding_mode=%s tags=%s", grounding_mode, dict(tags or {}))

    def output_contract_usage(self, *, output_format: str, tags: Mapping[str, str] | None = None) -> None:
        self._logger.debug("metric=output_contract_usage value=1 output_format=%s tags=%s", output_format, dict(tags or {}))

    def prompt_failures(self, *, error_type: str, tags: Mapping[str, str] | None = None) -> None:
        self._logger.debug("metric=prompt_failures value=1 error_type=%s tags=%s", error_type, dict(tags or {}))
