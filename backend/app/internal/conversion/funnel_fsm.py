"""Deterministic funnel stage FSM with guard-based transition evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from app.internal.conversion.policy_enums import JourneyStage


@dataclass(frozen=True, slots=True)
class FunnelTransitionInput:
    """Inputs used for stage guard checks."""

    trust_score: float
    persona_label: str
    intent: str
    persona_confidence: float


@dataclass(frozen=True, slots=True)
class GuardCheck:
    """Single guard evaluation for transparent stage decisioning."""

    guard: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class FunnelTransitionResult:
    """Structured output for allowed/disallowed stage transition decisions."""

    current_stage: JourneyStage
    target_stage: JourneyStage
    next_stage: JourneyStage
    allowed: bool
    reason: str
    guard_checks: tuple[GuardCheck, ...]


@dataclass(frozen=True, slots=True)
class FunnelFSMConfig:
    """Configurable thresholds and intent gates for funnel progression."""

    min_trust_by_stage: Mapping[JourneyStage, float] = field(
        default_factory=lambda: {
            JourneyStage.ENTRY: 0.0,
            JourneyStage.EXPLORATION: 0.05,
            JourneyStage.TRUST_FORMATION: 0.20,
            JourneyStage.OPPORTUNITY_AWARENESS: 0.35,
            JourneyStage.MICRO_COMMITMENT: 0.50,
            JourneyStage.ECONOMIC_ACTION: 0.72,
        }
    )
    required_intents: Mapping[JourneyStage, tuple[str, ...]] = field(
        default_factory=lambda: {
            JourneyStage.EXPLORATION: ("explore", "curious", "learn"),
            JourneyStage.TRUST_FORMATION: ("clarify", "trust", "understand"),
            JourneyStage.OPPORTUNITY_AWARENESS: ("opportunity", "value", "fit"),
            JourneyStage.MICRO_COMMITMENT: ("trial", "next_step", "micro_commit"),
            JourneyStage.ECONOMIC_ACTION: ("buy", "purchase", "pricing", "economic"),
        }
    )
    stage_order: tuple[JourneyStage, ...] = (
        JourneyStage.ENTRY,
        JourneyStage.EXPLORATION,
        JourneyStage.TRUST_FORMATION,
        JourneyStage.OPPORTUNITY_AWARENESS,
        JourneyStage.MICRO_COMMITMENT,
        JourneyStage.ECONOMIC_ACTION,
    )


class FunnelStageFSM:
    """Deterministic FSM that allows only sequential forward progression."""

    def __init__(self, config: FunnelFSMConfig | None = None) -> None:
        self.config = config or FunnelFSMConfig()
        self._index = {stage: idx for idx, stage in enumerate(self.config.stage_order)}

    def evaluate_transition(
        self,
        *,
        current_stage: JourneyStage,
        target_stage: JourneyStage,
        data: FunnelTransitionInput,
    ) -> FunnelTransitionResult:
        """Evaluate stage transition with strict sequencing and configurable guards."""

        current_idx = self._index[current_stage]
        target_idx = self._index[target_stage]

        if target_idx == current_idx:
            return FunnelTransitionResult(
                current_stage=current_stage,
                target_stage=target_stage,
                next_stage=current_stage,
                allowed=True,
                reason="same_stage",
                guard_checks=(),
            )

        if target_idx < current_idx:
            return FunnelTransitionResult(
                current_stage=current_stage,
                target_stage=target_stage,
                next_stage=current_stage,
                allowed=False,
                reason="backward_transition_disallowed",
                guard_checks=(),
            )

        if target_idx > current_idx + 1:
            return FunnelTransitionResult(
                current_stage=current_stage,
                target_stage=target_stage,
                next_stage=current_stage,
                allowed=False,
                reason="non_sequential_jump_disallowed",
                guard_checks=(
                    GuardCheck(
                        guard="sequential_progression",
                        passed=False,
                        detail="target must be immediate next stage",
                    ),
                ),
            )

        # Immediate next-stage guard checks.
        intent_text = data.intent.strip().lower()
        required_trust = self.config.min_trust_by_stage.get(target_stage, 0.0)
        intent_options = self.config.required_intents.get(target_stage, ())

        trust_ok = data.trust_score >= required_trust
        intent_ok = any(token in intent_text for token in intent_options) if intent_options else True

        checks = (
            GuardCheck(
                guard="trust_threshold",
                passed=trust_ok,
                detail=f"trust={data.trust_score:.3f} required={required_trust:.3f}",
            ),
            GuardCheck(
                guard="intent_alignment",
                passed=intent_ok,
                detail=f"intent='{intent_text}' required_any={list(intent_options)}",
            ),
        )

        if trust_ok and intent_ok:
            return FunnelTransitionResult(
                current_stage=current_stage,
                target_stage=target_stage,
                next_stage=target_stage,
                allowed=True,
                reason="guard_checks_passed",
                guard_checks=checks,
            )

        return FunnelTransitionResult(
            current_stage=current_stage,
            target_stage=target_stage,
            next_stage=current_stage,
            allowed=False,
            reason="guard_checks_failed",
            guard_checks=checks,
        )

    def suggest_next_stage(self, *, current_stage: JourneyStage, data: FunnelTransitionInput) -> FunnelTransitionResult:
        """Evaluate progression to the immediate next stage and return decision."""

        current_idx = self._index[current_stage]
        if current_idx >= len(self.config.stage_order) - 1:
            return FunnelTransitionResult(
                current_stage=current_stage,
                target_stage=current_stage,
                next_stage=current_stage,
                allowed=True,
                reason="terminal_stage",
                guard_checks=(),
            )

        target = self.config.stage_order[current_idx + 1]
        return self.evaluate_transition(current_stage=current_stage, target_stage=target, data=data)
