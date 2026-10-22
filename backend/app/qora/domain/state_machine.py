from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Mapping

from app.qora.domain.enums import ConversationStage


class InvalidTransitionError(ValueError):
    pass


class StageContextError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StageDefinition:
    stage: ConversationStage
    entry_conditions: tuple[str, ...]
    allowed_transitions: frozenset[ConversationStage]
    required_context: frozenset[str]
    actions: tuple[str, ...]
    exit_conditions: tuple[str, ...]
    fallback: ConversationStage
    timeout: timedelta
    analytics_event: str

    def validate(self, context: Mapping[str, Any]) -> None:
        missing = [key for key in self.required_context if context.get(key) is None]
        if missing:
            raise StageContextError(f"Missing stage context: {', '.join(sorted(missing))}")


_FLOW = list(ConversationStage)


def _stage(
    value: ConversationStage,
    *,
    required: tuple[str, ...] = (),
    actions: tuple[str, ...] = (),
    fallback: ConversationStage | None = None,
    extra: tuple[ConversationStage, ...] = (),
    timeout_minutes: int = 30,
) -> StageDefinition:
    index = _FLOW.index(value)
    next_stage = _FLOW[index + 1] if index + 1 < len(_FLOW) else ConversationStage.SIGNAL_CAPTURE
    allowed = {value, next_stage, *extra}
    return StageDefinition(
        stage=value,
        entry_conditions=(f"entered_from_allowed_transition",),
        allowed_transitions=frozenset(allowed),
        required_context=frozenset(required),
        actions=actions,
        exit_conditions=("stage_actions_completed", "required_context_valid"),
        fallback=fallback or value,
        timeout=timedelta(minutes=timeout_minutes),
        analytics_event=f"QORA_STAGE_{value.value}",
    )


STAGE_DEFINITIONS: dict[ConversationStage, StageDefinition] = {
    ConversationStage.START: _stage(ConversationStage.START, actions=("load_or_create_state",)),
    ConversationStage.GREETING: _stage(ConversationStage.GREETING, actions=("safe_short_intro", "prohibit_product", "prohibit_wallet")),
    ConversationStage.WHAT_IS_THIS: _stage(ConversationStage.WHAT_IS_THIS, actions=("frame_ecosystem_paths", "preserve_user_agency")),
    ConversationStage.SIGNAL_CAPTURE: _stage(ConversationStage.SIGNAL_CAPTURE, required=("signals_parsed",), actions=("parse_text", "parse_behavior", "persist_signals")),
    ConversationStage.PERSONA_CLASSIFICATION: _stage(ConversationStage.PERSONA_CLASSIFICATION, required=("persona_assessed",), actions=("score_persona", "hide_persona")),
    ConversationStage.MODIFIER_CLASSIFICATION: _stage(ConversationStage.MODIFIER_CLASSIFICATION, required=("modifiers_assessed",), actions=("evaluate_multilabel_modifiers",)),
    ConversationStage.DEPTH_SELECTION: _stage(ConversationStage.DEPTH_SELECTION, required=("depth_selected",), actions=("apply_depth_policy",)),
    ConversationStage.SECTION_DISCOVERY: _stage(ConversationStage.SECTION_DISCOVERY, required=("section_decision",), actions=("route_section",), extra=(ConversationStage.SIGNAL_CAPTURE,)),
    ConversationStage.NEED_QUALIFICATION: _stage(ConversationStage.NEED_QUALIFICATION, required=("qualification_status",), actions=("ask_high_information_question",), extra=(ConversationStage.SECTION_DISCOVERY, ConversationStage.SIGNAL_CAPTURE)),
    ConversationStage.WEIGHT_MATCHING: _stage(ConversationStage.WEIGHT_MATCHING, required=("qualification_complete", "weight_version"), actions=("load_official_weights",), fallback=ConversationStage.NEED_QUALIFICATION),
    ConversationStage.PRODUCT_PRIORITIZATION: _stage(ConversationStage.PRODUCT_PRIORITIZATION, required=("ranking_decision",), actions=("rank_eligible_products", "apply_safety"), fallback=ConversationStage.NEED_QUALIFICATION),
    ConversationStage.PRODUCT_INTRODUCTION: _stage(ConversationStage.PRODUCT_INTRODUCTION, required=("qualified_product", "rag_result"), actions=("retrieve_product_truth", "compose_grounded_intro"), fallback=ConversationStage.NEED_QUALIFICATION),
    ConversationStage.ACHIEVEMENT_OVERLAY: _stage(ConversationStage.ACHIEVEMENT_OVERLAY, required=("achievement_evaluated",), actions=("apply_eligible_overlay",)),
    ConversationStage.CTA: _stage(ConversationStage.CTA, required=("cta_policy",), actions=("select_primary_cta", "limit_secondary_cta")),
    ConversationStage.NEXT_BEST_ACTION: _stage(ConversationStage.NEXT_BEST_ACTION, required=("next_best_action",), actions=("persist_nba",)),
    ConversationStage.FEEDBACK_OBSERVATION: _stage(ConversationStage.FEEDBACK_OBSERVATION, required=("feedback_observed",), actions=("record_behavior",)),
    ConversationStage.PERSONA_REASSESSMENT: _stage(ConversationStage.PERSONA_REASSESSMENT, required=("persona_reassessed",), actions=("apply_stable_transition_only",), extra=(ConversationStage.SIGNAL_CAPTURE,)),
}


class ConversationStateMachine:
    def definition(self, stage: ConversationStage) -> StageDefinition:
        return STAGE_DEFINITIONS[stage]

    def transition(
        self,
        *,
        current: ConversationStage,
        target: ConversationStage,
        context: Mapping[str, Any],
    ) -> ConversationStage:
        definition = self.definition(current)
        definition.validate(context)
        if target not in definition.allowed_transitions:
            raise InvalidTransitionError(f"Transition {current.value} -> {target.value} is not allowed")
        return target

    def timeout_target(self, stage: ConversationStage) -> ConversationStage:
        return self.definition(stage).fallback

    def describe(self) -> list[dict[str, Any]]:
        return [
            {
                "stage": item.stage.value,
                "entry_conditions": list(item.entry_conditions),
                "allowed_transitions": sorted(stage.value for stage in item.allowed_transitions),
                "required_context": sorted(item.required_context),
                "actions": list(item.actions),
                "exit_conditions": list(item.exit_conditions),
                "fallback": item.fallback.value,
                "timeout_seconds": int(item.timeout.total_seconds()),
                "analytics_event": item.analytics_event,
            }
            for item in STAGE_DEFINITIONS.values()
        ]
