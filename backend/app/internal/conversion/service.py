"""Conversion funnel orchestration service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

from app.internal.conversion.enums import FunnelStage, TriggerType
from app.internal.conversion.conversion_policy import ConversionPolicyInput
from app.internal.conversion.cta_gatekeeper import CTAGatekeeper
from app.internal.conversion.funnel_fsm import FunnelStageFSM, FunnelTransitionInput
from app.internal.conversion.orchestration_models import ConversionFunnelRequest, ConversionFunnelResponse
from app.internal.conversion.policy_enums import JourneyStage
from app.internal.conversion.repositories.interfaces import ConversionEventRepository, FunnelStateRepository
from app.internal.conversion.trigger_selector import TriggerSelectionEngine, TriggerSelectionInput
from app.internal.conversion.trust_engine import update_trust_score
from app.internal.policy.config_models import PersonaConversionPolicyConfig
from app.internal.policy.loader import load_default_policy_config


class ConversionEventEmitter(Protocol):
    """Event emitter contract used by conversion orchestration."""

    def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        """Emit a structured conversion event payload."""


class NoopConversionEventEmitter:
    """Default no-op conversion event emitter."""

    def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        _ = event_name
        _ = payload


class ConversionFunnelService:
    """Orchestrates trust update, stage evaluation, trigger selection, and CTA gating."""

    def __init__(
        self,
        *,
        fsm: FunnelStageFSM | None = None,
        trigger_engine: TriggerSelectionEngine | None = None,
        cta_gatekeeper: CTAGatekeeper | None = None,
        funnel_state_repository: FunnelStateRepository | None = None,
        conversion_event_repository: ConversionEventRepository | None = None,
        policy_config: PersonaConversionPolicyConfig | None = None,
        event_emitter: ConversionEventEmitter | None = None,
    ) -> None:
        self.policy_config = policy_config or load_default_policy_config()
        self.fsm = fsm or FunnelStageFSM()
        self.trigger_engine = trigger_engine or TriggerSelectionEngine()
        self.cta_gatekeeper = cta_gatekeeper or CTAGatekeeper()
        self.funnel_state_repository = funnel_state_repository
        self.conversion_event_repository = conversion_event_repository
        self.event_emitter = event_emitter or NoopConversionEventEmitter()

    async def update(self, request: ConversionFunnelRequest) -> ConversionFunnelResponse:
        """Run deterministic conversion funnel orchestration pipeline."""

        trust_cfg = self.policy_config.conversion.trust.deltas
        trust_result = update_trust_score(
            current_score=request.trust_score,
            repeated_interaction_count=request.repeated_interaction_count,
            clarification_success_count=request.clarification_success_count,
            objection_count=request.objection_count,
            confusion_count=request.confusion_count,
            deltas=trust_cfg,
        )

        stage_data = FunnelTransitionInput(
            trust_score=trust_result.updated_score,
            persona_label=request.persona_label,
            intent=request.intent,
            persona_confidence=request.persona_confidence,
        )
        stage_result = self.fsm.suggest_next_stage(current_stage=request.current_stage, data=stage_data)

        trigger_result = self.trigger_engine.select(
            TriggerSelectionInput(
                persona_label=request.persona_label,
                stage=stage_result.next_stage,
                trust_score=trust_result.updated_score,
                intent=request.intent,
            )
        )

        cta_decision = self.cta_gatekeeper.evaluate(
            ConversionPolicyInput(
                persona_label=request.persona_label,
                persona_confidence=request.persona_confidence,
                trust_score=trust_result.updated_score,
                stage=stage_result.next_stage,
                intent=request.intent,
                is_ambiguous=request.is_ambiguous,
            )
        )

        self._persist_state(request, stage_result.next_stage, trust_result.updated_score)
        self._emit_events(request, trust_result.updated_score, stage_result.next_stage, trigger_result.primary_trigger.value)

        metadata = {
            "stage_reason": stage_result.reason,
            "guard_checks": [
                {
                    "guard": check.guard,
                    "passed": check.passed,
                    "detail": check.detail,
                }
                for check in stage_result.guard_checks
            ],
            "trust_reasons": [
                {
                    "code": reason.code,
                    "delta": reason.delta,
                    "detail": reason.detail,
                }
                for reason in trust_result.reasons
            ],
            "trigger_reason": trigger_result.reason,
            "trigger_metadata": dict(trigger_result.metadata),
            "cta_explanation": dict(cta_decision.explanation),
        }

        return ConversionFunnelResponse(
            session_id=request.session_id,
            previous_trust_score=trust_result.previous_score,
            updated_trust_score=trust_result.updated_score,
            previous_stage=request.current_stage,
            next_stage=stage_result.next_stage,
            stage_transition_allowed=stage_result.allowed,
            primary_trigger=trigger_result.primary_trigger,
            secondary_trigger=trigger_result.secondary_trigger,
            allowed_actions=list(cta_decision.allowed_actions),
            blocked_reasons=list(cta_decision.blocked_reasons),
            orchestration_metadata=metadata,
        )

    def _persist_state(self, request: ConversionFunnelRequest, stage: JourneyStage, trust_score: float) -> None:
        if self.funnel_state_repository is None:
            return

        funnel_stage = _to_funnel_stage(stage)
        payload: dict[str, Any] = {
            "session_id": request.session_id,
            "stage": funnel_stage,
            "stage_confidence": request.persona_confidence,
            "cta_allowed": True,
            "state_payload": {
                "trust_score": trust_score,
                "persona_label": request.persona_label,
                "intent": request.intent,
            },
        }
        if request.user_id is not None:
            try:
                payload["user_id"] = UUID(request.user_id)
            except ValueError:
                payload["user_id"] = None

        state = self.funnel_state_repository.upsert(payload)

        if self.conversion_event_repository is not None:
            self.conversion_event_repository.create(
                {
                    "session_id": state.session_id,
                    "funnel_state_id": state.id,
                    "event_type": TriggerType.CTA_OFFER,
                    "stage": funnel_stage,
                    "persona_type": None,
                    "metadata_json": {
                        "trust_score": trust_score,
                        "intent": request.intent,
                    },
                    "source": "conversion_funnel_service",
                    "created_at": datetime.now(timezone.utc),
                }
            )

    def _emit_events(self, request: ConversionFunnelRequest, trust_score: float, stage: JourneyStage, trigger: str) -> None:
        self.event_emitter.emit(
            "conversion.trust_updated",
            {
                "session_id": request.session_id,
                "trust_score": trust_score,
            },
        )
        self.event_emitter.emit(
            "conversion.stage_evaluated",
            {
                "session_id": request.session_id,
                "stage": stage.value,
            },
        )
        self.event_emitter.emit(
            "conversion.trigger_selected",
            {
                "session_id": request.session_id,
                "trigger": trigger,
            },
        )


def _to_funnel_stage(stage: JourneyStage) -> FunnelStage:
    mapping = {
        JourneyStage.ENTRY: FunnelStage.AWARENESS,
        JourneyStage.EXPLORATION: FunnelStage.AWARENESS,
        JourneyStage.TRUST_FORMATION: FunnelStage.CONSIDERATION,
        JourneyStage.OPPORTUNITY_AWARENESS: FunnelStage.INTENT,
        JourneyStage.MICRO_COMMITMENT: FunnelStage.DECISION,
        JourneyStage.ECONOMIC_ACTION: FunnelStage.CONVERSION,
    }
    return mapping.get(stage, FunnelStage.AWARENESS)
