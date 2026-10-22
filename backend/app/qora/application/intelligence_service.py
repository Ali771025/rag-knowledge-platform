from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select

from app.qora.application.state_service import QoraStateService
from app.qora.domain.contracts import DepthPolicy, ModifierDecision, PersonaDecision, SignalParserResult
from app.qora.domain.depth import DepthController
from app.qora.domain.enums import ConversationStage, PersonaCore, PersonaModifier
from app.qora.domain.persona.engine import PersonaScoringEngine
from app.qora.domain.persona.modifiers import ModifierEngine
from app.qora.domain.persona.reassessment import PersonaReassessmentEngine, ReassessmentDecision
from app.qora.domain.signals.parser import HybridSignalParser, SignalInput
from app.qora.infrastructure.persistence.models import PersonaAssessment


@dataclass(frozen=True, slots=True)
class BehavioralIntelligenceResult:
    signals: SignalParserResult
    persona: PersonaDecision
    modifiers: tuple[ModifierDecision, ...]
    depth: DepthPolicy
    reassessment: ReassessmentDecision
    state_version: int


class BehavioralIntelligenceService:
    """Coordinates deterministic QORA intelligence and durable state updates."""

    def __init__(self, state_service: QoraStateService, parser: HybridSignalParser) -> None:
        self.state_service = state_service
        self.parser = parser
        self.scorer = PersonaScoringEngine(state_service.policy)
        self.modifier_engine = ModifierEngine(state_service.policy)
        self.depth_controller = DepthController()
        self.reassessment_engine = PersonaReassessmentEngine(state_service.policy)

    def analyze(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        request_id: str,
        signal_input: SignalInput,
        turn_id: UUID | None = None,
    ) -> BehavioralIntelligenceResult:
        state = self.state_service.get_or_create_state(
            user_id=user_id,
            conversation_id=conversation_id,
            request_id=request_id,
        )
        parsed = self.parser.parse(signal_input)
        for signal in parsed.signals:
            self.state_service.append_signal(
                user_id=user_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                signal_code=signal.code,
                signal_category=signal.category,
                signal_strength=signal.strength,
                source_type=signal.source,
                source_value=signal.evidence,
                metadata=signal.metadata,
                request_id=request_id,
            )

        history_length = len(self.state_service.cumulative_signals(user_id=user_id))
        scoring = self.scorer.evaluate(
            previous_scores=state.persona_scores,
            signals=parsed.signals,
            history_length=history_length,
            ambiguity_score=parsed.ambiguity_score,
        )
        current_modifiers = tuple(PersonaModifier(item) for item in state.persona_modifiers)
        modifier_turns = self._modifier_active_turns(conversation_id, current_modifiers)
        modifier_result = self.modifier_engine.evaluate(
            signals=parsed.signals,
            currently_active=current_modifiers,
            active_turns=modifier_turns,
        )
        candidate = scoring.decision.candidate_personas[0] if scoring.decision.candidate_personas else None
        current_persona = PersonaCore(state.persona_core) if state.persona_core else None
        reassessment = self.reassessment_engine.evaluate(
            current_persona=current_persona,
            candidate_persona=candidate,
            scores=scoring.decision.scores,
            consecutive_candidate_assessments=self._candidate_streak(conversation_id, candidate) + 1,
            confidence=scoring.decision.confidence,
        )
        depth = self.depth_controller.resolve(
            persona=reassessment.selected_persona,
            modifiers=modifier_result.active_modifiers,
            confidence=scoring.decision.confidence,
        )
        self.state_service.record_assessment(
            user_id=user_id,
            conversation_id=conversation_id,
            persona_scores={persona.value: score for persona, score in scoring.decision.scores.items()},
            selected_persona=candidate,
            modifiers=list(modifier_result.active_modifiers),
            confidence=scoring.decision.confidence,
            evidence=[{"signal_code": code} for code in scoring.decision.evidence],
            assessment_version="qora-persona-v1",
            request_id=request_id,
        )
        state = self.state_service.load_state(user_id=user_id, conversation_id=conversation_id)
        updated = self.state_service.update_state(
            user_id=user_id,
            conversation_id=conversation_id,
            expected_version=state.version,
            request_id=request_id,
            changes={
                "persona_core": reassessment.selected_persona.value if reassessment.selected_persona else None,
                "persona_scores": {persona.value: score for persona, score in scoring.decision.scores.items()},
                "persona_modifiers": [item.value for item in modifier_result.active_modifiers],
                "persona_confidence": scoring.decision.confidence,
                "depth_level": depth.level.value,
                "conversation_stage": (
                    ConversationStage.PERSONA_REASSESSMENT.value
                    if reassessment.transition_allowed and current_persona is not None
                    else ConversationStage.DEPTH_SELECTION.value
                ),
            },
        )
        public_persona = scoring.decision.model_copy(update={"persona_core": reassessment.selected_persona})
        return BehavioralIntelligenceResult(
            signals=parsed,
            persona=public_persona,
            modifiers=modifier_result.decisions,
            depth=depth,
            reassessment=reassessment,
            state_version=updated.version,
        )

    def _candidate_streak(self, conversation_id: UUID, candidate: PersonaCore | None) -> int:
        if candidate is None:
            return 0
        assessments = list(
            self.state_service.session.scalars(
                select(PersonaAssessment)
                .where(PersonaAssessment.conversation_id == conversation_id)
                .order_by(PersonaAssessment.created_at.desc())
                .limit(self.state_service.policy.scoring.minimum_transition_evidence)
            ).all()
        )
        streak = 0
        for assessment in assessments:
            if assessment.selected_persona != candidate.value:
                break
            streak += 1
        return streak

    def _modifier_active_turns(
        self,
        conversation_id: UUID,
        modifiers: tuple[PersonaModifier, ...],
    ) -> dict[PersonaModifier, int]:
        if not modifiers:
            return {}
        assessments = list(
            self.state_service.session.scalars(
                select(PersonaAssessment)
                .where(PersonaAssessment.conversation_id == conversation_id)
                .order_by(PersonaAssessment.created_at.desc())
                .limit(max(rule.minimum_duration_turns for rule in self.state_service.policy.modifier_rules.values()))
            ).all()
        )
        result: dict[PersonaModifier, int] = {}
        for modifier in modifiers:
            count = 0
            for assessment in assessments:
                if modifier.value not in assessment.modifiers:
                    break
                count += 1
            result[modifier] = count
        return result

