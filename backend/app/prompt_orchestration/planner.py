"""Deterministic prompt-planning rules for strategy selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from app.prompt_orchestration.context_models import OnboardingStage
from app.prompt_orchestration.exceptions import PromptContractError
from app.prompt_orchestration.strategies import (
    BaseStrategySelector,
    PromptStrategyType,
    StrategyEvaluation,
    StrategySelectionRequest,
    StrategySelectionResult,
)


def _validate_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise PromptContractError(f"`{field_name}` must be a non-empty string.")
    return normalized


def _to_frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


class InteractionType(StrEnum):
    """Supported interaction types used by the planner."""

    ONBOARDING = "onboarding"
    QNA = "qna"
    TROUBLESHOOTING = "troubleshooting"
    SUMMARIZATION = "summarization"
    CONTINUATION = "continuation"
    NEXT_STEP = "next_step"


class IntentType(StrEnum):
    """Supported normalized intent labels used by the planner."""

    ONBOARDING_HELP = "onboarding_help"
    ASK_QUESTION = "ask_question"
    CLARIFY = "clarify"
    TROUBLESHOOT = "troubleshoot"
    SUMMARIZE = "summarize"
    CONTINUE = "continue"
    NEXT_STEP = "next_step"


@dataclass(frozen=True, slots=True)
class PromptPlanningResult:
    """Planning outcome from deterministic rule-based selection."""

    request_id: str
    selected_strategy: PromptStrategyType
    planning_notes: tuple[str, ...]
    signals: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _validate_non_empty(self.request_id, "request_id"))
        if not self.planning_notes:
            raise PromptContractError("`planning_notes` cannot be empty.")
        normalized_notes = tuple(_validate_non_empty(note, "planning_notes[]") for note in self.planning_notes)
        object.__setattr__(self, "planning_notes", normalized_notes)
        object.__setattr__(self, "signals", _to_frozen_mapping(self.signals))


@dataclass(frozen=True, slots=True)
class PromptPlannerFallbackConfig:
    """Configurable fallback strategy mapping for non-decisive requests."""

    with_retrieved_context: PromptStrategyType = PromptStrategyType.RAG_ANSWER
    with_history_only: PromptStrategyType = PromptStrategyType.CONTINUATION
    with_no_context: PromptStrategyType = PromptStrategyType.CLARIFICATION


class PromptPlanner(BaseStrategySelector):
    """Deterministic prompt planner.

    The planner is intentionally transparent and rule-based.
    It does not rely on any ML classifier.
    """

    def __init__(self, fallback_config: PromptPlannerFallbackConfig | None = None) -> None:
        self._fallback_config = fallback_config or PromptPlannerFallbackConfig()

    def plan(self, request: StrategySelectionRequest) -> PromptPlanningResult:
        interaction_type = self._parse_interaction_type(request.metadata.get("interaction_type"))
        intent = self._parse_intent(request.metadata.get("intent"))
        onboarding_stage = self._parse_onboarding_stage(request.metadata.get("onboarding_stage"))
        has_retrieved_context = self._resolve_has_retrieved_context(request)

        if interaction_type is InteractionType.SUMMARIZATION and not request.conversation_history and not has_retrieved_context:
            raise PromptContractError(
                "Unsupported combination: summarization requires conversation history or retrieved context."
            )
        if interaction_type is InteractionType.ONBOARDING and onboarding_stage is OnboardingStage.COMPLETED:
            raise PromptContractError(
                "Unsupported combination: onboarding interaction is invalid when onboarding_stage is completed."
            )
        if interaction_type is InteractionType.QNA and intent is IntentType.SUMMARIZE:
            raise PromptContractError("Unsupported combination: qna interaction cannot use summarize intent.")

        strategy, notes = self._select_strategy(
            interaction_type=interaction_type,
            intent=intent,
            onboarding_stage=onboarding_stage,
            has_retrieved_context=has_retrieved_context,
            has_history=bool(request.conversation_history),
        )

        if strategy not in request.allowed_strategies:
            allowed = ", ".join(item.value for item in request.allowed_strategies)
            raise PromptContractError(
                f"Planner selected unsupported strategy `{strategy.value}` for request; allowed strategies: {allowed}"
            )

        signals = {
            "interaction_type": interaction_type.value if interaction_type else None,
            "intent": intent.value if intent else None,
            "onboarding_stage": onboarding_stage.value if onboarding_stage else None,
            "has_retrieved_context": has_retrieved_context,
            "history_size": len(request.conversation_history),
        }
        return PromptPlanningResult(
            request_id=request.request_id,
            selected_strategy=strategy,
            planning_notes=tuple(notes),
            signals=signals,
        )

    def select_strategy(self, request: StrategySelectionRequest) -> StrategySelectionResult:
        """Compatibility with the Phase 3 selector contract."""
        plan = self.plan(request)
        return StrategySelectionResult(
            request_id=plan.request_id,
            selected_strategy=plan.selected_strategy,
            evaluations=(StrategyEvaluation(strategy_type=plan.selected_strategy, score=1.0),),
            rationale="; ".join(plan.planning_notes),
            metadata=plan.signals,
        )

    def _parse_interaction_type(self, value: Any) -> InteractionType | None:
        if value is None:
            return None
        try:
            return InteractionType(str(value).strip().lower())
        except ValueError as exc:
            options = ", ".join(item.value for item in InteractionType)
            raise PromptContractError(f"Unsupported interaction_type `{value}`. Supported values: {options}.") from exc

    def _parse_intent(self, value: Any) -> IntentType | None:
        if value is None:
            return None
        try:
            return IntentType(str(value).strip().lower())
        except ValueError as exc:
            options = ", ".join(item.value for item in IntentType)
            raise PromptContractError(f"Unsupported intent `{value}`. Supported values: {options}.") from exc

    def _parse_onboarding_stage(self, value: Any) -> OnboardingStage | None:
        if value is None:
            return None
        try:
            return OnboardingStage(str(value).strip().lower())
        except ValueError as exc:
            options = ", ".join(item.value for item in OnboardingStage)
            raise PromptContractError(f"Unsupported onboarding_stage `{value}`. Supported values: {options}.") from exc

    def _resolve_has_retrieved_context(self, request: StrategySelectionRequest) -> bool:
        explicit = request.metadata.get("has_retrieved_context")
        if isinstance(explicit, bool):
            return explicit
        return bool(request.context_snippets)

    def _select_strategy(
        self,
        *,
        interaction_type: InteractionType | None,
        intent: IntentType | None,
        onboarding_stage: OnboardingStage | None,
        has_retrieved_context: bool,
        has_history: bool,
    ) -> tuple[PromptStrategyType, list[str]]:
        notes: list[str] = ["Deterministic planner v1 used metadata and context signals."]

        if interaction_type is InteractionType.ONBOARDING or intent is IntentType.ONBOARDING_HELP:
            if onboarding_stage in {OnboardingStage.NOT_STARTED, OnboardingStage.IN_PROGRESS, None}:
                notes.append("Onboarding signal detected; selecting onboarding_guidance.")
                return PromptStrategyType.ONBOARDING_GUIDANCE, notes

        if interaction_type is InteractionType.TROUBLESHOOTING or intent is IntentType.TROUBLESHOOT:
            notes.append("Troubleshooting signal detected; selecting troubleshooting strategy.")
            return PromptStrategyType.TROUBLESHOOTING, notes

        if interaction_type is InteractionType.SUMMARIZATION or intent is IntentType.SUMMARIZE:
            notes.append("Summarization signal detected; selecting summarization strategy.")
            return PromptStrategyType.SUMMARIZATION, notes

        if interaction_type is InteractionType.NEXT_STEP or intent is IntentType.NEXT_STEP:
            notes.append("Next-step signal detected; selecting next_best_step strategy.")
            return PromptStrategyType.NEXT_BEST_STEP, notes

        if interaction_type is InteractionType.CONTINUATION or intent is IntentType.CONTINUE:
            notes.append("Continuation signal detected; selecting continuation strategy.")
            return PromptStrategyType.CONTINUATION, notes

        if interaction_type is InteractionType.QNA or intent is IntentType.ASK_QUESTION:
            if has_retrieved_context:
                notes.append("QnA with retrieved context; selecting rag_answer strategy.")
                return PromptStrategyType.RAG_ANSWER, notes
            notes.append("QnA without retrieved context; selecting clarification strategy.")
            return PromptStrategyType.CLARIFICATION, notes

        # Metadata is either absent or not decisive; choose from stable fallbacks.
        if has_retrieved_context:
            selected = self._fallback_config.with_retrieved_context
            notes.append(f"No explicit interaction metadata; retrieved context present, selecting {selected.value}.")
            return selected, notes
        if has_history:
            selected = self._fallback_config.with_history_only
            notes.append(f"No explicit interaction metadata; conversation history present, selecting {selected.value}.")
            return selected, notes

        selected = self._fallback_config.with_no_context
        notes.append(f"No explicit interaction metadata or context; selecting {selected.value}.")
        return selected, notes
