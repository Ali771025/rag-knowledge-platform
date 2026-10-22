"""Prompt strategy taxonomy and strategy-selection contracts.

This module intentionally defines interfaces and typed request/result models only.
It does not implement concrete strategy logic, ranking rules, or templates.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from app.prompt_orchestration.exceptions import PromptContractError
from app.prompt_orchestration.models import PromptBuildRequest, PromptBuildResult, PromptMessage


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


class PromptStrategyType(StrEnum):
    """Supported prompt strategy categories."""

    ONBOARDING_GUIDANCE = "onboarding_guidance"
    RAG_ANSWER = "rag_answer"
    CLARIFICATION = "clarification"
    NEXT_BEST_STEP = "next_best_step"
    TROUBLESHOOTING = "troubleshooting"
    SUMMARIZATION = "summarization"
    CONTINUATION = "continuation"


SUPPORTED_PROMPT_STRATEGIES: tuple[PromptStrategyType, ...] = tuple(PromptStrategyType)


@dataclass(frozen=True, slots=True)
class StrategySelectionRequest:
    """Domain request for selecting an orchestration strategy."""

    request_id: str
    user_input: str
    conversation_history: tuple[PromptMessage, ...] = ()
    context_snippets: tuple[str, ...] = ()
    allowed_strategies: tuple[PromptStrategyType, ...] = SUPPORTED_PROMPT_STRATEGIES
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _validate_non_empty(self.request_id, "request_id"))
        object.__setattr__(self, "user_input", _validate_non_empty(self.user_input, "user_input"))

        snippets = tuple(_validate_non_empty(snippet, "context_snippets[]") for snippet in self.context_snippets)
        object.__setattr__(self, "context_snippets", snippets)

        if not self.allowed_strategies:
            raise PromptContractError("`allowed_strategies` cannot be empty.")
        if len(set(self.allowed_strategies)) != len(self.allowed_strategies):
            raise PromptContractError("`allowed_strategies` cannot contain duplicates.")

        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class StrategyEvaluation:
    """A selector's evaluation signal for one strategy candidate."""

    strategy_type: PromptStrategyType
    score: float
    rationale: str | None = None

    def __post_init__(self) -> None:
        if self.score < 0 or self.score > 1:
            raise PromptContractError("`score` must be between 0 and 1.")
        object.__setattr__(self, "rationale", _validate_optional_non_empty(self.rationale, "rationale"))


@dataclass(frozen=True, slots=True)
class StrategySelectionResult:
    """Domain result for strategy-selection decisions."""

    request_id: str
    selected_strategy: PromptStrategyType
    evaluations: tuple[StrategyEvaluation, ...] = ()
    rationale: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _validate_non_empty(self.request_id, "request_id"))
        object.__setattr__(self, "rationale", _validate_optional_non_empty(self.rationale, "rationale"))

        if self.evaluations:
            evaluated = {item.strategy_type for item in self.evaluations}
            if self.selected_strategy not in evaluated:
                raise PromptContractError("`selected_strategy` must be present in `evaluations` when provided.")

        object.__setattr__(self, "metadata", _to_frozen_mapping(self.metadata))


class PromptStrategy(Protocol):
    """Interface for strategy-specific prompt builders."""

    strategy_type: PromptStrategyType

    def build_prompt(self, request: PromptBuildRequest) -> PromptBuildResult:
        """Build a prompt result using this strategy."""


class StrategySelector(Protocol):
    """Interface for selecting which strategy should handle a request."""

    def select_strategy(self, request: StrategySelectionRequest) -> StrategySelectionResult:
        """Select a strategy for the given request."""


class BasePromptStrategy(ABC):
    """Abstract base class for concrete strategy implementations."""

    strategy_type: PromptStrategyType

    @abstractmethod
    def build_prompt(self, request: PromptBuildRequest) -> PromptBuildResult:
        """Build a prompt result using this strategy."""


class BaseStrategySelector(ABC):
    """Abstract base class for strategy-selector implementations."""

    @abstractmethod
    def select_strategy(self, request: StrategySelectionRequest) -> StrategySelectionResult:
        """Select a strategy for the given request."""

