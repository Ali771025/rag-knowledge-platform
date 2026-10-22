"""Persona intelligence orchestration service and integration hooks."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol
from uuid import UUID

from app.internal.persona.confidence_engine import evaluate_persona_confidence
from app.internal.persona.enums import PersonaModifier, PersonaType
from app.internal.persona.events import PersonaAnalyzedEvent, PersonaModifierAppliedEvent
from app.internal.persona.modifier_detector import detect_persona_modifiers
from app.internal.persona.orchestration_models import (
    PersonaIntelligenceRequest,
    PersonaIntelligenceResponse,
    PersonaTransitionSummary,
)
from app.internal.persona.persona_scorer import score_persona_signals
from app.internal.persona.repositories.interfaces import (
    ModifierHistoryRepository,
    PersonaHistoryRepository,
    PersonaStateRepository,
)
from app.internal.persona.signal_extractor import extract_persona_signals
from app.internal.persona.transition_manager import PersonaTransitionManager
from app.internal.policy.config_models import PersonaConversionPolicyConfig
from app.internal.policy.loader import load_default_policy_config


class PersonaEventEmitter(Protocol):
    """Event emitter contract used by persona intelligence orchestration."""

    def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        """Emit a structured event payload for side-channel consumers."""


class NoopPersonaEventEmitter:
    """Default no-op emitter to keep orchestration wiring optional."""

    def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        _ = event_name
        _ = payload


class PersonaIntelligenceService:
    """Assembles signal extraction, scoring, confidence, modifiers, and transition checks."""

    def __init__(
        self,
        *,
        transition_manager: PersonaTransitionManager,
        state_repository: PersonaStateRepository | None = None,
        history_repository: PersonaHistoryRepository | None = None,
        modifier_history_repository: ModifierHistoryRepository | None = None,
        policy_config: PersonaConversionPolicyConfig | None = None,
        event_emitter: PersonaEventEmitter | None = None,
    ) -> None:
        self.transition_manager = transition_manager
        self.state_repository = state_repository
        self.history_repository = history_repository
        self.modifier_history_repository = modifier_history_repository
        self.policy_config = policy_config or load_default_policy_config()
        self.event_emitter = event_emitter or NoopPersonaEventEmitter()

    async def analyze(self, request: PersonaIntelligenceRequest) -> PersonaIntelligenceResponse:
        """Run the full persona intelligence pipeline and package structured output."""

        current_state = self._load_current_state(request)
        current_persona = self._resolve_current_persona(request, current_state)

        extraction_cfg = self.policy_config.persona.signal_extraction
        score_cfg = self.policy_config.persona.scoring
        modifier_cfg = self.policy_config.persona.modifier_detection

        history_messages = [
            *request.recent_messages[-2:],
            request.message,
        ]
        extracted_history = [
            extract_persona_signals(
                message=text,
                metadata=request.metadata if index == len(history_messages) - 1 else {},
                hesitation_terms=extraction_cfg.hesitation_terms,
                proof_terms=extraction_cfg.proof_terms,
                roi_terms=extraction_cfg.roi_terms,
                analytical_terms=extraction_cfg.analytical_terms,
                urgency_terms=extraction_cfg.urgency_terms,
                gamification_terms=extraction_cfg.gamification_terms,
                lexical_terms=extraction_cfg.lexical_terms,
                keyword_cap=extraction_cfg.keyword_cap,
                metadata_weights=extraction_cfg.metadata_weights,
            )
            for index, text in enumerate(history_messages)
        ]

        scoring_result = score_persona_signals(
            extracted_history,
            signal_weights=score_cfg.signal_weights,
            decay_factor_base=score_cfg.decay_factor_base,
        )
        confidence = evaluate_persona_confidence(
            scoring_result.persona_scores,
            threshold=score_cfg.confidence_neutral_threshold,
        )
        modifiers = detect_persona_modifiers(
            message=request.message,
            metadata=request.metadata,
            rules=modifier_cfg.rules,
        )

        candidate_persona = confidence.top_persona or current_persona
        transition = await self.transition_manager.evaluate_transition(
            session_id=request.session_id,
            current_persona=current_persona,
            candidate_persona=candidate_persona,
            persona_scores=scoring_result.persona_scores,
            confidence=max(0.0, confidence.confidence_gap),
            modifiers=modifiers.active_modifiers,
            signal_summary={
                signal.value: value for signal, value in extracted_history[-1].normalized_signals().items()
            },
            source="persona_intelligence_service",
        )

        assigned_persona = confidence.assigned_persona or current_persona
        state_record = self._persist_state(
            request=request,
            assigned_persona=assigned_persona,
            confidence_score=confidence.top_score,
            modifiers=modifiers.active_modifiers,
            signal_summary={signal.value: value for signal, value in extracted_history[-1].signals.items()},
            previous_state=current_state,
            transition=transition,
            modifier_evaluations=modifiers.evaluations,
        )

        self._emit_events(
            request=request,
            assigned_persona=assigned_persona,
            confidence=confidence.top_score,
            modifiers=modifiers.active_modifiers,
            transition=transition,
        )

        transition_summary = PersonaTransitionSummary(
            candidate_persona=transition.candidate_persona,
            recommendation_allowed=transition.recommendation_allowed,
            transition_allowed=transition.transition_allowed,
            score_ratio=transition.score_ratio,
            stable_evidence_count=transition.stable_evidence_count,
            reasons=[item.code for item in transition.reasons],
        )

        orchestration_metadata = {
            "current_persona": current_persona.value,
            "candidate_persona": candidate_persona.value,
            "state_persisted": state_record is not None,
            "history_message_count": len(history_messages),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        dialogue_hints = {
            "persona_label": assigned_persona.value,
            "low_confidence": confidence.is_low_confidence,
            "active_modifiers": [item.value for item in modifiers.active_modifiers],
            "transition_recommended": transition.recommendation_allowed,
            "transition_allowed": transition.transition_allowed,
        }

        return PersonaIntelligenceResponse(
            session_id=request.session_id,
            assigned_persona=assigned_persona,
            assignment_label=confidence.assignment_label,
            is_low_confidence=confidence.is_low_confidence,
            confidence_gap=confidence.confidence_gap,
            confidence_threshold=confidence.threshold,
            persona_scores=dict(scoring_result.persona_scores),
            modifiers=list(modifiers.active_modifiers),
            transition=transition_summary,
            dialogue_hints=dialogue_hints,
            orchestration_metadata=orchestration_metadata,
        )

    def _load_current_state(self, request: PersonaIntelligenceRequest) -> Any | None:
        if self.state_repository is None:
            return None
        return self.state_repository.get_by_session_id(request.session_id)

    @staticmethod
    def _resolve_current_persona(request: PersonaIntelligenceRequest, state_record: Any | None) -> PersonaType:
        if request.current_persona is not None:
            return request.current_persona
        if state_record is not None and isinstance(getattr(state_record, "persona_type", None), PersonaType):
            return state_record.persona_type
        return PersonaType.EXPLORER

    def _persist_state(
        self,
        *,
        request: PersonaIntelligenceRequest,
        assigned_persona: PersonaType,
        confidence_score: float,
        modifiers: tuple[PersonaModifier, ...],
        signal_summary: dict[str, float],
        previous_state: Any | None,
        transition: Any,
        modifier_evaluations: Mapping[PersonaModifier, Any],
    ) -> Any | None:
        if self.state_repository is None:
            return None

        payload: dict[str, Any] = {
            "session_id": request.session_id,
            "persona_type": assigned_persona,
            "confidence": confidence_score,
            "active_modifiers": [modifier.value for modifier in modifiers],
            "signals_json": signal_summary,
        }
        if request.user_id is not None:
            try:
                payload["user_id"] = UUID(request.user_id)
            except ValueError:
                payload["user_id"] = None

        saved = self.state_repository.upsert(payload)

        if self.history_repository is not None:
            previous_persona = None
            if previous_state is not None and isinstance(getattr(previous_state, "persona_type", None), PersonaType):
                previous_persona = previous_state.persona_type
            self.history_repository.create(
                {
                    "persona_state_id": saved.id,
                    "session_id": saved.session_id,
                    "previous_persona_type": previous_persona,
                    "new_persona_type": assigned_persona,
                    "confidence": confidence_score,
                    "rationale": ", ".join(reason.code for reason in transition.reasons),
                }
            )

        if self.modifier_history_repository is not None:
            for modifier, evaluation in modifier_evaluations.items():
                self.modifier_history_repository.create(
                    {
                        "persona_state_id": saved.id,
                        "session_id": saved.session_id,
                        "modifier": modifier,
                        "is_applied": evaluation.is_active,
                        "trigger_type": None,
                        "details_json": {
                            "score": evaluation.score,
                            "threshold": evaluation.threshold,
                            "keyword_hits": list(evaluation.keyword_hits),
                            "metadata_hits": list(evaluation.metadata_hits),
                            "explanation": evaluation.explanation,
                        },
                    }
                )

        return saved

    def _emit_events(
        self,
        *,
        request: PersonaIntelligenceRequest,
        assigned_persona: PersonaType,
        confidence: float,
        modifiers: tuple[PersonaModifier, ...],
        transition: Any,
    ) -> None:
        analyzed = PersonaAnalyzedEvent(
            session_id=request.session_id,
            persona_type=assigned_persona,
            confidence=confidence,
        )
        self.event_emitter.emit(analyzed.event_name, analyzed.model_dump(mode="json"))

        for modifier in modifiers:
            event = PersonaModifierAppliedEvent(
                session_id=request.session_id,
                modifier=modifier,
                threshold=self.policy_config.persona.modifier_thresholds.get(modifier, 0.0),
            )
            self.event_emitter.emit(event.event_name, event.model_dump(mode="json"))

        self.event_emitter.emit(
            "persona.transition_evaluated",
            {
                "session_id": request.session_id,
                "candidate_persona": transition.candidate_persona.value,
                "recommendation_allowed": transition.recommendation_allowed,
                "transition_allowed": transition.transition_allowed,
                "score_ratio": transition.score_ratio,
                "reasons": [asdict(reason) for reason in transition.reasons],
            },
        )
