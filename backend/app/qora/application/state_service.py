from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.qora.application.errors import (
    DuplicateEventError,
    InvalidStateUpdateError,
    StateNotFoundError,
    StateVersionConflictError,
)
from app.qora.config import QoraPolicyConfig, load_qora_policy
from app.qora.domain.enums import (
    ConversationStage,
    DepthLevel,
    PersonaCore,
    PersonaModifier,
    QoraEventType,
    Section,
    SignalSourceType,
    TurnRole,
)
from app.qora.infrastructure.persistence.models import (
    AgentUserState,
    ConversationTurn,
    DetectedSignal,
    PersonaAssessment,
    RecommendationDecision,
    UserInteractionEvent,
)
from app.qora.infrastructure.persistence.privacy import mask_sensitive, mask_text
from app.qora.infrastructure.persistence.repositories import (
    AssessmentRepository,
    EventRepository,
    RecommendationRepository,
    SignalRepository,
    StateRepository,
    TurnRepository,
)

_PERSONA_ADAPTER = TypeAdapter(PersonaCore)
_MODIFIER_ADAPTER = TypeAdapter(list[PersonaModifier])
_DEPTH_ADAPTER = TypeAdapter(DepthLevel)
_STAGE_ADAPTER = TypeAdapter(ConversationStage)
_SECTION_ADAPTER = TypeAdapter(Section)

_MUTABLE_STATE_FIELDS = {
    "persona_core",
    "persona_scores",
    "persona_modifiers",
    "depth_level",
    "persona_confidence",
    "selected_section",
    "current_intent",
    "intent_confidence",
    "conversation_stage",
    "matched_product",
    "product_priority_reason",
    "next_best_action",
    "current_points",
    "current_level",
    "readiness_score",
    "reward_sensitivity",
}


class QoraStateService:
    """Single transactional access point for QORA state and append-only history."""

    def __init__(self, session: Session, policy: QoraPolicyConfig | None = None) -> None:
        self.session = session
        self.policy = policy or load_qora_policy()
        self.states = StateRepository(session)
        self.signals = SignalRepository(session)
        self.events = EventRepository(session)
        self.turns = TurnRepository(session)
        self.assessments = AssessmentRepository(session)
        self.recommendations = RecommendationRepository(session)

    def get_or_create_state(self, *, user_id: UUID, conversation_id: UUID, request_id: str) -> AgentUserState:
        existing = self.states.load(user_id=user_id, conversation_id=conversation_id)
        if existing is not None:
            return existing

        state = AgentUserState(
            user_id=user_id,
            conversation_id=conversation_id,
            persona_scores={persona.value: 0.0 for persona in PersonaCore},
        )
        try:
            self.states.create(state)
            self._append_event_model(
                user_id=user_id,
                conversation_id=conversation_id,
                event_type=QoraEventType.STATE_CREATED,
                entity_type="AgentUserState",
                entity_id=str(state.id),
                metadata={"snapshot": self._state_payload(state)},
                request_id=request_id,
                idempotency_key=f"state-created:{conversation_id}",
            )
            self.session.commit()
            return state
        except IntegrityError:
            self.session.rollback()
            concurrent = self.states.load(user_id=user_id, conversation_id=conversation_id)
            if concurrent is None:
                raise
            return concurrent
        except Exception:
            self.session.rollback()
            raise

    def load_state(self, *, user_id: UUID, conversation_id: UUID) -> AgentUserState:
        state = self.states.load(user_id=user_id, conversation_id=conversation_id)
        if state is None:
            raise StateNotFoundError("QORA state was not found")
        return state

    def update_state(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        expected_version: int,
        changes: dict[str, Any],
        request_id: str,
        idempotency_key: str | None = None,
    ) -> AgentUserState:
        state = self.load_state(user_id=user_id, conversation_id=conversation_id)
        validated = self._validate_changes(changes)
        if state.version != expected_version:
            self.session.rollback()
            raise StateVersionConflictError(
                f"State version conflict: expected {expected_version}, current {state.version}"
            )
        try:
            updated = self.states.compare_and_swap(
                state_id=state.id,
                expected_version=expected_version,
                values=validated,
            )
            if not updated:
                raise StateVersionConflictError(f"State version {expected_version} is stale")
            self._append_event_model(
                user_id=user_id,
                conversation_id=conversation_id,
                event_type=QoraEventType.STATE_UPDATED,
                entity_type="AgentUserState",
                entity_id=str(state.id),
                metadata={"changes": validated, "from_version": expected_version, "to_version": expected_version + 1},
                request_id=request_id,
                idempotency_key=idempotency_key,
            )
            self.session.commit()
            return self.load_state(user_id=user_id, conversation_id=conversation_id)
        except Exception:
            self.session.rollback()
            raise

    def append_signal(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        signal_code: str,
        signal_category: str,
        signal_strength: float,
        source_type: SignalSourceType,
        request_id: str,
        turn_id: UUID | None = None,
        source_value: str | None = None,
        expires_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DetectedSignal:
        if signal_strength < 0.0 or signal_strength > 1.0:
            raise ValueError("signal_strength must be between 0 and 1")
        if expires_at is None and signal_category not in self.policy.signal_windows.stable_signal_categories:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=self.policy.signal_windows.default_ttl_hours)
        signal = DetectedSignal(
            user_id=user_id,
            conversation_id=conversation_id,
            turn_id=turn_id,
            signal_code=signal_code,
            signal_category=signal_category,
            signal_strength=signal_strength,
            source_type=source_type.value,
            source_value=mask_text(source_value),
            expires_at=expires_at,
            metadata_json=mask_sensitive(metadata or {}),
        )
        try:
            self.signals.append(signal)
            self._append_event_model(
                user_id=user_id,
                conversation_id=conversation_id,
                event_type=QoraEventType.SIGNAL_DETECTED,
                entity_type="DetectedSignal",
                entity_id=str(signal.id),
                metadata={
                    "signal_code": signal_code,
                    "signal_category": signal_category,
                    "signal_strength": signal_strength,
                    "source_type": source_type.value,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                },
                request_id=request_id,
            )
            self.session.commit()
            return signal
        except Exception:
            self.session.rollback()
            raise

    def append_event(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        event_type: str,
        request_id: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        event_id: str | None = None,
        idempotency_key: str | None = None,
        occurred_at: datetime | None = None,
    ) -> UserInteractionEvent:
        if idempotency_key and self.events.by_idempotency_key(user_id=user_id, key=idempotency_key):
            self.session.rollback()
            raise DuplicateEventError("Duplicate idempotency key")
        try:
            event = self._append_event_model(
                user_id=user_id,
                conversation_id=conversation_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                metadata=metadata or {},
                request_id=request_id,
                event_id=event_id,
                idempotency_key=idempotency_key,
                occurred_at=occurred_at,
            )
            self.session.commit()
            return event
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateEventError("Duplicate event_id or idempotency key") from exc
        except Exception:
            self.session.rollback()
            raise

    def record_turn(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        role: TurnRole,
        message: str,
        normalized_message: str | None,
        stage_before: ConversationStage,
        stage_after: ConversationStage,
        request_id: str,
    ) -> ConversationTurn:
        turn = ConversationTurn(
            user_id=user_id,
            conversation_id=conversation_id,
            role=role.value,
            message=mask_text(message) or "",
            normalized_message=mask_text(normalized_message),
            stage_before=stage_before.value,
            stage_after=stage_after.value,
            request_id=request_id,
        )
        try:
            self.turns.append(turn)
            self._append_event_model(
                user_id=user_id,
                conversation_id=conversation_id,
                event_type=QoraEventType.TURN_RECORDED,
                entity_type="ConversationTurn",
                entity_id=str(turn.id),
                metadata={"role": role.value, "stage_before": stage_before.value, "stage_after": stage_after.value},
                request_id=request_id,
            )
            self.session.commit()
            return turn
        except Exception:
            self.session.rollback()
            raise

    def record_assessment(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        persona_scores: dict[str, float],
        selected_persona: PersonaCore | None,
        modifiers: list[PersonaModifier],
        confidence: float,
        evidence: list[dict[str, Any]],
        assessment_version: str,
        request_id: str,
    ) -> PersonaAssessment:
        assessment = PersonaAssessment(
            user_id=user_id,
            conversation_id=conversation_id,
            persona_scores=persona_scores,
            selected_persona=selected_persona.value if selected_persona else None,
            modifiers=[item.value for item in modifiers],
            confidence=confidence,
            evidence=mask_sensitive(evidence),
            assessment_version=assessment_version,
        )
        try:
            self.assessments.append(assessment)
            self._append_event_model(
                user_id=user_id,
                conversation_id=conversation_id,
                event_type=QoraEventType.PERSONA_ASSESSED,
                entity_type="PersonaAssessment",
                entity_id=str(assessment.id),
                metadata={
                    "persona_scores": persona_scores,
                    "selected_persona": selected_persona.value if selected_persona else None,
                    "modifiers": [item.value for item in modifiers],
                    "confidence": confidence,
                    "assessment_version": assessment_version,
                },
                request_id=request_id,
            )
            self.session.commit()
            return assessment
        except Exception:
            self.session.rollback()
            raise

    def record_recommendation(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        selected_section: Section,
        persona_core: PersonaCore | None,
        ranked_products: list[dict[str, Any]],
        matched_product: dict[str, Any] | None,
        weight_snapshot: dict[str, Any],
        priority_reason: str | None,
        next_best_action: dict[str, Any] | None,
        confidence: float,
        request_id: str,
    ) -> RecommendationDecision:
        decision = RecommendationDecision(
            user_id=user_id,
            conversation_id=conversation_id,
            selected_section=selected_section.value,
            persona_core=persona_core.value if persona_core else None,
            ranked_products=mask_sensitive(ranked_products),
            matched_product=mask_sensitive(matched_product),
            weight_snapshot=mask_sensitive(weight_snapshot),
            priority_reason=mask_text(priority_reason),
            next_best_action=mask_sensitive(next_best_action),
            confidence=confidence,
        )
        try:
            self.recommendations.append(decision)
            self._append_event_model(
                user_id=user_id,
                conversation_id=conversation_id,
                event_type=QoraEventType.RECOMMENDATION_RECORDED,
                entity_type="RecommendationDecision",
                entity_id=str(decision.id),
                metadata={
                    "selected_section": selected_section.value,
                    "persona_core": persona_core.value if persona_core else None,
                    "matched_product": matched_product,
                    "priority_reason": priority_reason,
                    "next_best_action": next_best_action,
                    "confidence": confidence,
                },
                request_id=request_id,
            )
            self.session.commit()
            return decision
        except Exception:
            self.session.rollback()
            raise

    def rolling_signals(self, *, user_id: UUID, conversation_id: UUID) -> list[DetectedSignal]:
        return self.signals.rolling(
            user_id=user_id,
            conversation_id=conversation_id,
            turn_limit=self.policy.signal_windows.short_term_turns,
        )

    def cumulative_signals(self, *, user_id: UUID, include_expired: bool = False) -> list[DetectedSignal]:
        return self.signals.cumulative(
            user_id=user_id,
            behavioral_days=self.policy.signal_windows.behavioral_days,
            include_expired=include_expired,
        )

    def history(self, *, user_id: UUID, conversation_id: UUID) -> list[UserInteractionEvent]:
        return self.events.history(user_id=user_id, conversation_id=conversation_id)

    def rebuild_state(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        request_id: str,
    ) -> AgentUserState:
        current = self.load_state(user_id=user_id, conversation_id=conversation_id)
        rebuilt: dict[str, Any] = {
            "persona_core": None,
            "persona_scores": {persona.value: 0.0 for persona in PersonaCore},
            "persona_modifiers": [],
            "depth_level": DepthLevel.LOW.value,
            "persona_confidence": 0.0,
            "selected_section": None,
            "current_intent": None,
            "intent_confidence": 0.0,
            "conversation_stage": ConversationStage.START.value,
            "matched_product": None,
            "product_priority_reason": None,
            "next_best_action": None,
            "current_points": 0,
            "current_level": 1,
            "readiness_score": 0.0,
            "reward_sensitivity": 0.0,
        }
        history = self.history(user_id=user_id, conversation_id=conversation_id)
        for event in history:
            if event.event_type == QoraEventType.STATE_CREATED.value:
                rebuilt.update(event.metadata_json.get("snapshot", {}))
            elif event.event_type == QoraEventType.STATE_UPDATED.value:
                rebuilt.update(event.metadata_json.get("changes", {}))

        rebuilt = {key: value for key, value in rebuilt.items() if key in _MUTABLE_STATE_FIELDS}
        try:
            if not self.states.compare_and_swap(
                state_id=current.id,
                expected_version=current.version,
                values=self._validate_changes(rebuilt),
            ):
                raise StateVersionConflictError("State changed while rebuild was running")
            self._append_event_model(
                user_id=user_id,
                conversation_id=conversation_id,
                event_type=QoraEventType.STATE_REBUILT,
                entity_type="AgentUserState",
                entity_id=str(current.id),
                metadata={"source_event_count": len(history), "from_version": current.version},
                request_id=request_id,
            )
            self.session.commit()
            return self.load_state(user_id=user_id, conversation_id=conversation_id)
        except Exception:
            self.session.rollback()
            raise

    def _append_event_model(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        event_type: str | QoraEventType,
        entity_type: str | None,
        entity_id: str | None,
        metadata: dict[str, Any],
        request_id: str,
        event_id: str | None = None,
        idempotency_key: str | None = None,
        occurred_at: datetime | None = None,
    ) -> UserInteractionEvent:
        event = UserInteractionEvent(
            event_id=event_id or f"evt_{uuid4().hex}",
            user_id=user_id,
            conversation_id=conversation_id,
            event_type=event_type.value if isinstance(event_type, QoraEventType) else event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=mask_sensitive(metadata),
            occurred_at=occurred_at or datetime.now(timezone.utc),
            request_id=request_id,
            idempotency_key=idempotency_key,
        )
        return self.events.append(event)

    def _validate_changes(self, changes: dict[str, Any]) -> dict[str, Any]:
        unknown = set(changes) - _MUTABLE_STATE_FIELDS
        if unknown:
            raise InvalidStateUpdateError(f"Immutable or unknown state fields: {sorted(unknown)}")
        validated = dict(changes)
        try:
            if "persona_core" in validated and validated["persona_core"] is not None:
                validated["persona_core"] = _PERSONA_ADAPTER.validate_python(validated["persona_core"]).value
            if "persona_modifiers" in validated:
                validated["persona_modifiers"] = [
                    item.value for item in _MODIFIER_ADAPTER.validate_python(validated["persona_modifiers"])
                ]
            if "depth_level" in validated:
                validated["depth_level"] = _DEPTH_ADAPTER.validate_python(validated["depth_level"]).value
            if "conversation_stage" in validated:
                validated["conversation_stage"] = _STAGE_ADAPTER.validate_python(validated["conversation_stage"]).value
            if "selected_section" in validated and validated["selected_section"] is not None:
                validated["selected_section"] = _SECTION_ADAPTER.validate_python(validated["selected_section"]).value
        except ValidationError as exc:
            raise InvalidStateUpdateError("State enum validation failed") from exc
        for field in ("persona_confidence", "intent_confidence", "readiness_score", "reward_sensitivity"):
            if field in validated and not 0.0 <= float(validated[field]) <= 1.0:
                raise InvalidStateUpdateError(f"{field} must be between 0 and 1")
        if "persona_scores" in validated:
            score_keys = set(validated["persona_scores"])
            if score_keys != {persona.value for persona in PersonaCore}:
                raise InvalidStateUpdateError("persona_scores must contain all QORA personas")
        for field in ("matched_product", "next_best_action"):
            if field in validated:
                validated[field] = mask_sensitive(validated[field])
        if "product_priority_reason" in validated:
            validated["product_priority_reason"] = mask_text(validated["product_priority_reason"])
        return validated

    @staticmethod
    def _state_payload(state: AgentUserState) -> dict[str, Any]:
        return {field: getattr(state, field) for field in _MUTABLE_STATE_FIELDS}
