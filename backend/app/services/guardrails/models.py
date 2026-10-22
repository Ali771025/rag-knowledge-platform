"""Typed data models and contracts for Guardrails modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResponseStrategy(str, Enum):
    """High-level strategy selected by the safety orchestrator."""

    NORMAL = "normal"
    CLARIFY = "clarify"
    FALLBACK = "fallback"
    REJECT = "reject"


class FallbackAction(str, Enum):
    """Named fallback actions to keep behavior deterministic across modules."""

    LOW_CONFIDENCE = "low_confidence"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    OFF_TOPIC = "off_topic"
    BLOCKED_TOPIC = "blocked_topic"
    PROMPT_INJECTION = "prompt_injection"


class SafetyFlag(str, Enum):
    """Normalized safety signals emitted by guardrail checks."""

    LOW_CONFIDENCE = "low_confidence"
    OFF_TOPIC = "off_topic"
    BLOCKED_TOPIC = "blocked_topic"
    PROMPT_INJECTION = "prompt_injection"
    UNGROUNDED_CLAIM = "ungrounded_claim"
    OUTPUT_FILTERED = "output_filtered"


class RiskLevel(str, Enum):
    """Risk level used by injection and safety checks."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(slots=True)
class Document:
    id: str | None
    content: str
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ValidationResult:
    is_valid: bool
    confidence_score: float
    reason: str | None = None
    fallback_action: str | None = None


@dataclass(slots=True)
class OutputValidationResult:
    is_safe: bool
    confidence_score: float
    violations: list[str] = field(default_factory=list)
    filtered_response: str = ""


@dataclass(slots=True)
class OffTopicResult:
    is_off_topic: bool
    detected_topic: str | None = None
    confidence: float = 0.0


@dataclass(slots=True)
class InjectionResult:
    is_malicious: bool
    risk_level: str
    matched_patterns: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GroundingResult:
    is_grounded: bool
    unsupported_claims: list[str] = field(default_factory=list)
    grounding_score: float = 0.0


@dataclass(slots=True)
class SafetyOrchestratorResult:
    safe_response: str
    confidence: float
    safety_flags: list[str] = field(default_factory=list)
    fallback_used: bool = False
    response_strategy: str = "answer"


@dataclass(slots=True)
class PreSafetyResult:
    is_allowed: bool
    fallback_response: str | None = None
    safety_flags: list[str] = field(default_factory=list)
    reason: str | None = None
