from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.qora.application.frontend_mapper import FrontendResponseMapper
from app.qora.application.achievement_service import AchievementService
from app.qora.application.state_service import QoraStateService
from app.qora.domain.contracts import SignalCandidate
from app.qora.domain.depth import DepthController
from app.qora.domain.enums import (
    ConversationStage,
    DepthLevel,
    PersonaCore,
    PersonaModifier,
    Section,
    SignalSourceType,
    TurnRole,
)
from app.qora.domain.guardrails import QoraGuardrailValidator
from app.qora.domain.orchestration_contracts import (
    CompositionContext,
    InteractionEventInput,
    NextBestAction,
    OrchestratorResponse,
    PageContext,
    QualificationQuestion,
)
from app.qora.domain.persona.engine import PersonaScoringEngine
from app.qora.domain.persona.modifiers import ModifierEngine
from app.qora.domain.persona.reassessment import PersonaReassessmentEngine
from app.qora.domain.product_ranking import ProductPolicyItem, ProductRankingEngine
from app.qora.domain.qualification import QualificationEngine
from app.qora.domain.response_composer import ResponseComposer
from app.qora.domain.routing import IntentDetector, PRODUCT_SECTIONS, SectionRouter
from app.qora.domain.signals.parser import HybridSignalParser, SignalInput
from app.qora.domain.state_machine import ConversationStateMachine
from app.qora.infrastructure.persistence.models import (
    OrchestratorExecution,
    PersonaAssessment,
    ProductCatalogItem,
    QualificationAnswer,
)
from app.qora.infrastructure.persistence.orchestration_repositories import (
    ExecutionRepository,
    ProductPolicyRepository,
    QualificationRepository,
)
from app.qora.integrations.rag.client import NullRAGClient, QoraRAGClient, QoraRAGRequest, QoraRAGResult
from app.services.guardrails.prompt_injection_detector import detect_prompt_injection


class IdempotencyConflictError(ValueError):
    pass


class RequestInProgressError(RuntimeError):
    pass


class ConversationOrchestrator:
    def __init__(
        self,
        *,
        state_service: QoraStateService,
        signal_parser: HybridSignalParser | None = None,
        rag_client: QoraRAGClient | None = None,
        composer: ResponseComposer | None = None,
    ) -> None:
        self.state_service = state_service
        self.session = state_service.session
        self.executions = ExecutionRepository(self.session)
        self.qualifications = QualificationRepository(self.session)
        self.product_policy = ProductPolicyRepository(self.session)
        self.signal_parser = signal_parser or HybridSignalParser()
        self.rag_client = rag_client or NullRAGClient()
        self.composer = composer or ResponseComposer()
        self.mapper = FrontendResponseMapper()
        self.machine = ConversationStateMachine()
        self.intent_detector = IntentDetector()
        self.section_router = SectionRouter()
        self.qualification_engine = QualificationEngine()
        self.persona_engine = PersonaScoringEngine(state_service.policy)
        self.modifier_engine = ModifierEngine(state_service.policy)
        self.reassessment_engine = PersonaReassessmentEngine(state_service.policy)
        self.depth_controller = DepthController()
        self.ranking_engine = ProductRankingEngine()
        self.achievement_service = AchievementService(self.session, state_service.policy)
        self.guardrails = QoraGuardrailValidator()

    def process_turn(
        self,
        *,
        request_id: str,
        user_id: UUID,
        conversation_id: UUID,
        message: str,
        interaction_events: Sequence[InteractionEventInput | dict[str, Any]] = (),
        page_context: PageContext | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not request_id.strip():
            raise ValueError("request_id is required")
        normalized = self._normalize_message(message)
        page = page_context if isinstance(page_context, PageContext) else PageContext.model_validate(page_context or {})
        events = [
            item if isinstance(item, InteractionEventInput) else InteractionEventInput.model_validate(item)
            for item in interaction_events
        ]
        fingerprint = self._fingerprint(normalized, events, page)
        cached, execution = self._reserve_execution(
            request_id=request_id,
            user_id=user_id,
            conversation_id=conversation_id,
            fingerprint=fingerprint,
        )
        if cached is not None:
            return cached

        try:
            state = self.state_service.get_or_create_state(
                user_id=user_id, conversation_id=conversation_id, request_id=request_id
            )
            state = self._apply_timeout(state, user_id, conversation_id, request_id)
            execution.state_version_before = state.version
            self.session.commit()
            current_stage = ConversationStage(state.conversation_stage)
            self.state_service.record_turn(
                user_id=user_id,
                conversation_id=conversation_id,
                role=TurnRole.USER,
                message=message,
                normalized_message=normalized,
                stage_before=current_stage,
                stage_after=current_stage,
                request_id=request_id,
            )
            self._record_interactions(user_id, conversation_id, request_id, events)

            injection = detect_prompt_injection(normalized)
            if injection.is_malicious:
                response = self.composer.safe_fallback(
                    request_id=request_id,
                    conversation_id=str(conversation_id),
                    stage=current_stage,
                )
                response.warnings.append("PROMPT_INJECTION")
                self.state_service.record_turn(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    role=TurnRole.ASSISTANT,
                    message=response.message,
                    normalized_message=response.message,
                    stage_before=current_stage,
                    stage_after=current_stage,
                    request_id=request_id,
                )
                payload = self.mapper.map(response)
                execution = self.executions.get(
                    user_id=user_id, conversation_id=conversation_id, request_id=request_id
                )
                self.executions.complete(execution, payload, state.version)
                self.session.commit()
                return payload

            if current_stage == ConversationStage.START:
                final_stage = self._transition(
                    current_stage, ConversationStage.GREETING, {}, user_id, conversation_id, request_id
                )
                context = self._composition_context(state, final_stage, intent="GREETING")
                return self._finalize(execution, state, final_stage, context, message)
            if current_stage == ConversationStage.GREETING:
                final_stage = self._transition(
                    current_stage, ConversationStage.WHAT_IS_THIS, {}, user_id, conversation_id, request_id
                )
                context = self._composition_context(state, final_stage, intent="WHAT_IS_QORA")
                return self._finalize(execution, state, final_stage, context, message)

            signals = self._parse_and_persist_signals(
                user_id=user_id,
                conversation_id=conversation_id,
                request_id=request_id,
                normalized_message=normalized,
                events=events,
            )
            persona, persona_scores, persona_confidence, modifiers, depth = self._assess_behavior(
                state=state,
                signals=signals,
                user_id=user_id,
                conversation_id=conversation_id,
                request_id=request_id,
            )
            intent = self.intent_detector.detect(normalized)
            section_decision = self.section_router.resolve(
                intent=intent,
                signals=signals,
                explicit_section=page.explicit_section,
                explicit_product_id=page.explicit_product_id,
                page_context=page.model_dump(mode="python"),
                interaction_history=[item.model_dump(mode="python") for item in events],
                persona=persona,
            )
            selected_section = section_decision.selected_section or (
                Section(state.selected_section) if state.selected_section else None
            )
            if page.explicit_section and state.selected_section and page.explicit_section.value != state.selected_section:
                selected_section = page.explicit_section

            flags = {
                "signals_parsed": True,
                "persona_assessed": True,
                "modifiers_assessed": True,
                "depth_selected": True,
                "section_decision": section_decision.model_dump(mode="json"),
            }
            final_stage = self._advance_to_discovery(
                current_stage, flags, user_id, conversation_id, request_id
            )
            qualification_question: QualificationQuestion | None = None
            qualification_complete = False
            answers: dict[str, dict[str, Any]] = {}

            if selected_section is None:
                final_stage = ConversationStage.SECTION_DISCOVERY
            else:
                final_stage = self._enter_qualification(
                    final_stage, flags, user_id, conversation_id, request_id
                )
                pending = self.qualifications.pending(
                    user_id=user_id, conversation_id=conversation_id, section=selected_section
                )
                if pending and current_stage == ConversationStage.NEED_QUALIFICATION:
                    question = next(
                        item for item in self.qualification_engine.evaluate(
                            section=selected_section, answers={}, asked_codes=[]
                        ).next_questions if item.code == pending.question_code
                    )
                    answer_value, answer_confidence = self.qualification_engine.parse_answer(question, message)
                    self.qualifications.answer(pending, answer_value, answer_confidence, request_id)
                    self.session.commit()
                records = self.qualifications.list_for_section(
                    user_id=user_id, conversation_id=conversation_id, section=selected_section
                )
                answers = {
                    record.question_code: record.answer_value
                    for record in records
                    if record.status == "ANSWERED" and record.answer_value
                }
                status = self.qualification_engine.evaluate(
                    section=selected_section,
                    answers=answers,
                    asked_codes=[record.question_code for record in records],
                )
                qualification_complete = status.complete
                flags["qualification_status"] = status.model_dump(mode="json")
                flags["qualification_complete"] = status.complete
                if not status.complete:
                    qualification_question = self._ensure_question(
                        user_id, conversation_id, selected_section, status.next_questions[0], request_id
                    )

            rag_result = QoraRAGResult(insufficient_context=True)
            ranking = None
            matched_product: str | None = None
            priority_reason: str | None = None
            if selected_section and qualification_complete and persona is not None:
                version = self.product_policy.active_version()
                if version is not None:
                    flags["weight_version"] = version.weight_table_version
                    products = self.product_policy.products_for_section(selected_section)
                    weights = self.product_policy.weights(
                        version_id=version.id, section=selected_section, persona=persona
                    )
                    ranking = self.ranking_engine.rank(
                        section=selected_section,
                        persona=persona,
                        persona_confidence=persona_confidence,
                        products=[self._product_policy_item(item) for item in products],
                        persona_weights=weights,
                        weight_table_version=version.weight_table_version,
                        intent_confidence=intent.confidence,
                        qualification_complete=True,
                        qualification_match=self.qualification_engine.match_products(
                            section=selected_section,
                            answers=answers,
                            product_ids=[item.product_id for item in products],
                        ),
                        readiness_score=state.readiness_score,
                        behavior_match=self._behavior_match(signals),
                        modifiers=modifiers,
                        explicit_product_id=page.explicit_product_id,
                    )
                    flags["ranking_decision"] = ranking.model_dump(mode="json")
                    final_stage = self._advance_ranking(
                        final_stage, flags, user_id, conversation_id, request_id
                    )
                    if ranking.matched_product:
                        matched_product = ranking.matched_product.product_id
                        priority_reason = ranking.priority_reason
                        rag_result = self.rag_client.retrieve(
                            QoraRAGRequest(
                                product_id=matched_product,
                                selected_section=selected_section,
                                intent=intent.name,
                                depth_level=depth,
                                modifiers=modifiers,
                                language=page.language,
                            )
                        )
                        if not rag_result.insufficient_context and rag_result.sources:
                            flags["qualified_product"] = matched_product
                            flags["rag_result"] = True
                            final_stage = self._transition(
                                final_stage,
                                ConversationStage.PRODUCT_INTRODUCTION,
                                flags,
                                user_id,
                                conversation_id,
                                request_id,
                            )
                        self.state_service.record_recommendation(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            selected_section=selected_section,
                            persona_core=persona,
                            ranked_products=[item.model_dump(mode="json") for item in ranking.ranked_products],
                            matched_product=ranking.matched_product.model_dump(mode="json"),
                            weight_snapshot={
                                "weight_table_version": version.weight_table_version,
                                "weights": weights,
                            },
                            priority_reason=priority_reason,
                            next_best_action={"type": "VIEW_EXPLAINER"},
                            confidence=ranking.confidence,
                            request_id=request_id,
                        )

            nba = self._next_best_action(
                final_stage=final_stage,
                selected_section=selected_section,
                qualification_question=qualification_question,
                matched_product=matched_product,
                insufficient_context=rag_result.insufficient_context,
            )
            context = CompositionContext(
                persona_core=persona,
                modifiers=modifiers,
                depth_level=depth,
                intent=intent.name,
                selected_section=selected_section,
                matched_product=matched_product,
                priority_reason=priority_reason,
                conversation_stage=final_stage,
                rag_sources=rag_result.sources,
                rag_excerpt=rag_result.excerpt,
                insufficient_context=rag_result.insufficient_context,
                allowed_claims=rag_result.allowed_claims,
                forbidden_claims=["سود تضمینی", "بازده قطعی", "کاملاً قانونی"],
                next_best_action=nba,
                qualification_question=qualification_question,
                readiness_score=state.readiness_score,
            )
            final_stage, context = self._advance_post_product_stage(
                current_stage=current_stage,
                final_stage=final_stage,
                context=context,
                qualification_complete=qualification_complete,
                state=state,
                user_id=user_id,
                conversation_id=conversation_id,
                request_id=request_id,
            )
            changes = {
                "persona_core": persona.value if persona else state.persona_core,
                "persona_scores": persona_scores,
                "persona_modifiers": [item.value for item in modifiers],
                "depth_level": depth.value,
                "persona_confidence": persona_confidence,
                "selected_section": selected_section.value if selected_section else None,
                "current_intent": intent.name,
                "intent_confidence": intent.confidence,
                "conversation_stage": final_stage.value,
                "matched_product": {"product_id": matched_product} if matched_product and not rag_result.insufficient_context else None,
                "product_priority_reason": priority_reason,
                "next_best_action": nba.model_dump(mode="json") if nba else None,
            }
            latest = self.state_service.load_state(user_id=user_id, conversation_id=conversation_id)
            state = self.state_service.update_state(
                user_id=user_id,
                conversation_id=conversation_id,
                expected_version=latest.version,
                changes=changes,
                request_id=request_id,
                idempotency_key=f"orchestrator-state:{conversation_id}:{request_id}",
            )
            return self._finalize(execution, state, final_stage, context, message, state_already_updated=True)
        except Exception as exc:
            self.session.rollback()
            execution = self.executions.get(
                user_id=user_id, conversation_id=conversation_id, request_id=request_id
            )
            if execution is not None:
                self.executions.fail(execution, type(exc).__name__)
                self.session.commit()
            raise

    def _reserve_execution(
        self, *, request_id: str, user_id: UUID, conversation_id: UUID, fingerprint: str
    ) -> tuple[dict[str, Any] | None, OrchestratorExecution]:
        existing = self.executions.get(
            user_id=user_id, conversation_id=conversation_id, request_id=request_id
        )
        if existing:
            if existing.request_fingerprint != fingerprint:
                self.session.rollback()
                raise IdempotencyConflictError("request_id was already used with a different payload")
            if existing.status == "COMPLETED" and existing.response_payload is not None:
                cached = dict(existing.response_payload)
                self.session.rollback()
                return cached, existing
            self.session.rollback()
            raise RequestInProgressError("request is already in progress or failed")
        execution = OrchestratorExecution(
            user_id=user_id,
            conversation_id=conversation_id,
            request_id=request_id,
            request_fingerprint=fingerprint,
            status="IN_PROGRESS",
        )
        try:
            self.executions.create(execution)
            self.session.commit()
            return None, execution
        except IntegrityError:
            self.session.rollback()
            concurrent = self.executions.get(
                user_id=user_id, conversation_id=conversation_id, request_id=request_id
            )
            if concurrent and concurrent.status == "COMPLETED" and concurrent.response_payload:
                return dict(concurrent.response_payload), concurrent
            raise RequestInProgressError("concurrent request with same request_id")

    def _parse_and_persist_signals(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        request_id: str,
        normalized_message: str,
        events: Sequence[InteractionEventInput],
    ) -> list[SignalCandidate]:
        parsed = self.signal_parser.parse(SignalInput(user_text=normalized_message))
        signals = list(parsed.signals)
        for event in events:
            try:
                source = SignalSourceType(event.event_type)
            except ValueError:
                source = SignalSourceType.CLICK_EVENT
            event_result = self.signal_parser.parse(
                SignalInput(
                    source_type=source,
                    event_type=event.event_type,
                    source_value=event.entity_id,
                    metadata=event.metadata,
                )
            )
            signals.extend(event_result.signals)
        deduped: dict[str, SignalCandidate] = {}
        for signal in signals:
            current = deduped.get(signal.code)
            if current is None or signal.strength > current.strength:
                deduped[signal.code] = signal
        for signal in deduped.values():
            self.state_service.append_signal(
                user_id=user_id,
                conversation_id=conversation_id,
                signal_code=signal.code,
                signal_category=signal.category,
                signal_strength=signal.strength,
                source_type=signal.source,
                source_value=signal.evidence,
                metadata=signal.metadata,
                request_id=request_id,
            )
        return list(deduped.values())

    def _assess_behavior(
        self,
        *,
        state,
        signals: list[SignalCandidate],
        user_id: UUID,
        conversation_id: UUID,
        request_id: str,
    ) -> tuple[PersonaCore | None, dict[str, float], float, list[PersonaModifier], DepthLevel]:
        history_length = len(self.state_service.cumulative_signals(user_id=user_id))
        scoring = self.persona_engine.evaluate(
            previous_scores=state.persona_scores,
            signals=signals,
            history_length=history_length,
        )
        candidate = scoring.decision.candidate_personas[0] if scoring.decision.candidate_personas else None
        current = PersonaCore(state.persona_core) if state.persona_core else None
        reassessment = self.reassessment_engine.evaluate(
            current_persona=current,
            candidate_persona=scoring.decision.persona_core,
            scores=scoring.decision.scores,
            consecutive_candidate_assessments=self._candidate_streak(conversation_id, candidate) + 1,
            confidence=scoring.decision.confidence,
        )
        persona = reassessment.selected_persona
        modifier_result = self.modifier_engine.evaluate(
            signals=signals,
            currently_active=[PersonaModifier(item) for item in state.persona_modifiers],
            active_turns={PersonaModifier(item): 99 for item in state.persona_modifiers},
        )
        modifiers = list(modifier_result.active_modifiers)
        depth_policy = self.depth_controller.resolve(
            persona=persona,
            modifiers=modifiers,
            confidence=scoring.decision.confidence,
        )
        self.state_service.record_assessment(
            user_id=user_id,
            conversation_id=conversation_id,
            persona_scores={key.value: value for key, value in scoring.decision.scores.items()},
            selected_persona=candidate,
            modifiers=modifiers,
            confidence=scoring.decision.confidence,
            evidence=[{"signal_code": code} for code in scoring.decision.evidence],
            assessment_version="qora-persona-v1",
            request_id=request_id,
        )
        score_payload = {key.value: value for key, value in scoring.decision.scores.items()}
        return persona, score_payload, scoring.decision.confidence, modifiers, depth_policy.level

    def _advance_post_product_stage(
        self,
        *,
        current_stage,
        final_stage,
        context,
        qualification_complete,
        state,
        user_id,
        conversation_id,
        request_id,
    ):
        if not context.matched_product or context.insufficient_context:
            return final_stage, context
        flags = {
            "qualified_product": context.matched_product,
            "rag_result": True,
            "achievement_evaluated": True,
            "cta_policy": True,
            "next_best_action": context.next_best_action.model_dump(mode="json") if context.next_best_action else {},
            "feedback_observed": True,
            "persona_reassessed": True,
        }
        if current_stage == ConversationStage.PRODUCT_INTRODUCTION:
            achievement = self.achievement_service.get_next_best_achievement(state)
            level_card = self.achievement_service.level_card(
                state, achievement.context if achievement.eligible else None
            )
            flags["achievement_evaluated"] = list(achievement.reason_codes)
            final_stage = self._transition(
                ConversationStage.PRODUCT_INTRODUCTION,
                ConversationStage.ACHIEVEMENT_OVERLAY,
                flags,
                user_id,
                conversation_id,
                request_id,
            )
            if achievement.eligible and achievement.context:
                self.state_service.append_event(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    event_type="ACHIEVEMENT_SHOWN",
                    entity_type="ACHIEVEMENT",
                    entity_id=achievement.context.achievement_id,
                    metadata={"reason_codes": achievement.context.reason_codes},
                    request_id=request_id,
                    idempotency_key=f"achievement-shown:{conversation_id}:{request_id}",
                )
            context = context.model_copy(
                update={
                    "achievement_context": achievement.context if achievement.eligible else None,
                    "level_card": level_card,
                }
            )
        elif current_stage == ConversationStage.ACHIEVEMENT_OVERLAY:
            final_stage = self._transition(
                current_stage, ConversationStage.CTA, flags, user_id, conversation_id, request_id
            )
        elif current_stage == ConversationStage.CTA:
            final_stage = self._transition(
                current_stage, ConversationStage.NEXT_BEST_ACTION, flags, user_id, conversation_id, request_id
            )
        elif current_stage == ConversationStage.NEXT_BEST_ACTION:
            final_stage = self._transition(
                current_stage, ConversationStage.FEEDBACK_OBSERVATION, flags, user_id, conversation_id, request_id
            )
        elif current_stage == ConversationStage.FEEDBACK_OBSERVATION:
            final_stage = self._transition(
                current_stage, ConversationStage.PERSONA_REASSESSMENT, flags, user_id, conversation_id, request_id
            )
        elif current_stage == ConversationStage.PERSONA_REASSESSMENT:
            final_stage = self._transition(
                current_stage, ConversationStage.SIGNAL_CAPTURE, flags, user_id, conversation_id, request_id
            )
        return final_stage, context.model_copy(update={"conversation_stage": final_stage})

    def _advance_to_discovery(self, current, flags, user_id, conversation_id, request_id):
        stage = current
        if stage == ConversationStage.WHAT_IS_THIS:
            stage = self._transition(stage, ConversationStage.SIGNAL_CAPTURE, {}, user_id, conversation_id, request_id)
        ordered = [
            ConversationStage.SIGNAL_CAPTURE,
            ConversationStage.PERSONA_CLASSIFICATION,
            ConversationStage.MODIFIER_CLASSIFICATION,
            ConversationStage.DEPTH_SELECTION,
            ConversationStage.SECTION_DISCOVERY,
        ]
        if stage in ordered[:-1]:
            for target in ordered[ordered.index(stage) + 1 :]:
                stage = self._transition(stage, target, flags, user_id, conversation_id, request_id)
        if stage in {
            ConversationStage.PRODUCT_INTRODUCTION, ConversationStage.ACHIEVEMENT_OVERLAY,
            ConversationStage.CTA, ConversationStage.NEXT_BEST_ACTION, ConversationStage.FEEDBACK_OBSERVATION,
            ConversationStage.PERSONA_REASSESSMENT,
        }:
            return stage
        return stage

    def _enter_qualification(self, stage, flags, user_id, conversation_id, request_id):
        if stage == ConversationStage.SECTION_DISCOVERY:
            return self._transition(
                stage, ConversationStage.NEED_QUALIFICATION, flags, user_id, conversation_id, request_id
            )
        return stage

    def _advance_ranking(self, stage, flags, user_id, conversation_id, request_id):
        if stage == ConversationStage.NEED_QUALIFICATION:
            stage = self._transition(stage, ConversationStage.WEIGHT_MATCHING, flags, user_id, conversation_id, request_id)
        if stage == ConversationStage.WEIGHT_MATCHING:
            stage = self._transition(stage, ConversationStage.PRODUCT_PRIORITIZATION, flags, user_id, conversation_id, request_id)
        return stage

    def _transition(self, current, target, context, user_id, conversation_id, request_id):
        result = self.machine.transition(current=current, target=target, context=context)
        definition = self.machine.definition(target)
        self.state_service.append_event(
            user_id=user_id,
            conversation_id=conversation_id,
            event_type=definition.analytics_event,
            entity_type="ConversationStage",
            entity_id=target.value,
            metadata={"from_stage": current.value, "to_stage": target.value},
            request_id=request_id,
            idempotency_key=f"stage:{conversation_id}:{request_id}:{current.value}:{target.value}",
        )
        return result

    def _record_interactions(self, user_id, conversation_id, request_id, events):
        for index, event in enumerate(events):
            self.state_service.append_event(
                user_id=user_id,
                conversation_id=conversation_id,
                event_type=event.event_type,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                metadata=event.metadata,
                request_id=request_id,
                idempotency_key=event.idempotency_key or f"interaction:{conversation_id}:{request_id}:{index}",
            )

    def _ensure_question(self, user_id, conversation_id, section, question, request_id):
        pending = self.qualifications.pending(
            user_id=user_id, conversation_id=conversation_id, section=section
        )
        if pending:
            return question if pending.question_code == question.code else self._question_by_code(section, pending.question_code)
        record = QualificationAnswer(
            user_id=user_id,
            conversation_id=conversation_id,
            section=section.value,
            question_code=question.code,
            question_text=question.text,
            status="ASKED",
            confidence=0.0,
            request_id=request_id,
        )
        self.qualifications.ask(record)
        self.session.commit()
        return question

    def _question_by_code(self, section, code):
        status = self.qualification_engine.evaluate(section=section, answers={}, asked_codes=[])
        return next(item for item in status.next_questions if item.code == code)

    def _finalize(
        self,
        execution,
        state,
        final_stage,
        context,
        user_message,
        *,
        state_already_updated=False,
    ):
        response = self.composer.compose(
            request_id=execution.request_id,
            conversation_id=str(execution.conversation_id),
            context=context,
        )
        known_products = list(PRODUCT_SECTIONS)
        validation = self.guardrails.validate(
            response=response,
            context=context,
            user_message=user_message,
            known_product_ids=known_products,
        )
        if not validation.valid:
            response = self.composer.compose(
                request_id=execution.request_id,
                conversation_id=str(execution.conversation_id),
                context=context,
                force_safe=True,
            )
            validation = self.guardrails.validate(
                response=response,
                context=context,
                user_message=user_message,
                known_product_ids=known_products,
            )
        if not validation.valid:
            response = self.composer.safe_fallback(
                request_id=execution.request_id,
                conversation_id=str(execution.conversation_id),
                stage=final_stage,
            )
            response.warnings.extend(validation.reason_codes)
        if not state_already_updated:
            latest = self.state_service.load_state(
                user_id=execution.user_id, conversation_id=execution.conversation_id
            )
            state = self.state_service.update_state(
                user_id=execution.user_id,
                conversation_id=execution.conversation_id,
                expected_version=latest.version,
                changes={"conversation_stage": final_stage.value},
                request_id=execution.request_id,
                idempotency_key=f"orchestrator-state:{execution.conversation_id}:{execution.request_id}",
            )
        payload = self.mapper.map(response)
        self.state_service.record_turn(
            user_id=execution.user_id,
            conversation_id=execution.conversation_id,
            role=TurnRole.ASSISTANT,
            message=response.message,
            normalized_message=response.message,
            stage_before=final_stage,
            stage_after=final_stage,
            request_id=execution.request_id,
        )
        execution = self.executions.get(
            user_id=execution.user_id,
            conversation_id=execution.conversation_id,
            request_id=execution.request_id,
        )
        self.executions.complete(execution, payload, state.version)
        self.session.commit()
        return payload

    def _composition_context(self, state, stage, *, intent):
        return CompositionContext(
            persona_core=PersonaCore(state.persona_core) if state.persona_core else None,
            modifiers=[PersonaModifier(item) for item in state.persona_modifiers],
            depth_level=state.depth_level,
            intent=intent,
            selected_section=Section(state.selected_section) if state.selected_section else None,
            matched_product=None,
            conversation_stage=stage,
            rag_sources=[],
            insufficient_context=False,
            readiness_score=state.readiness_score,
        )

    def _next_best_action(self, *, final_stage, selected_section, qualification_question, matched_product, insufficient_context):
        if selected_section is None:
            return NextBestAction(type="SELECT_SECTION")
        if qualification_question is not None:
            return NextBestAction(
                type="ANSWER_QUALIFICATION", payload={"question_code": qualification_question.code}
            )
        if matched_product and insufficient_context:
            return NextBestAction(type="VIEW_OFFICIAL_DOCUMENTS", payload={"product_id": matched_product})
        if matched_product:
            return NextBestAction(type="VIEW_EXPLAINER", payload={"product_id": matched_product})
        if final_stage == ConversationStage.NEED_QUALIFICATION:
            return NextBestAction(type="CONTINUE_DISCOVERY")
        return None

    def _candidate_streak(self, conversation_id, candidate):
        if candidate is None:
            return 0
        rows = list(
            self.session.scalars(
                select(PersonaAssessment)
                .where(PersonaAssessment.conversation_id == conversation_id)
                .order_by(PersonaAssessment.created_at.desc())
                .limit(self.state_service.policy.scoring.minimum_transition_evidence)
            ).all()
        )
        count = 0
        for row in rows:
            if row.selected_persona != candidate.value:
                break
            count += 1
        return count

    def _apply_timeout(self, state, user_id, conversation_id, request_id):
        stage = ConversationStage(state.conversation_stage)
        updated_at = state.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        definition = self.machine.definition(stage)
        if datetime.now(timezone.utc) - updated_at <= definition.timeout:
            return state
        target = self.machine.timeout_target(stage)
        self.state_service.append_event(
            user_id=user_id,
            conversation_id=conversation_id,
            event_type="QORA_STAGE_TIMEOUT",
            entity_type="ConversationStage",
            entity_id=stage.value,
            metadata={"stage": stage.value, "fallback": target.value},
            request_id=request_id,
            idempotency_key=f"timeout:{conversation_id}:{request_id}:{stage.value}",
        )
        if target == stage:
            return state
        latest = self.state_service.load_state(user_id=user_id, conversation_id=conversation_id)
        return self.state_service.update_state(
            user_id=user_id,
            conversation_id=conversation_id,
            expected_version=latest.version,
            changes={"conversation_stage": target.value},
            request_id=request_id,
            idempotency_key=f"timeout-state:{conversation_id}:{request_id}",
        )

    @staticmethod
    def _behavior_match(signals: Sequence[SignalCandidate]) -> dict[str, float]:
        codes = {signal.code for signal in signals}
        scores: dict[str, float] = {}
        if codes & {"asks_about_risk", "asks_about_scam", "requests_terms"}:
            scores.update({"EID": 0.25, "Q": 0.20, "INSURANCE": 0.20})
        if codes & {"asks_about_level", "checks_progress", "asks_whats_next"}:
            scores.update({"EDGE": 0.25, "STAKING": 0.15, "ETER": 0.15})
        if codes & {"asks_design_reason", "asks_game_theory", "asks_incentive_structure"}:
            scores.update({"Q": 0.30, "PROPOSAL": 0.20, "ELITE": 0.20})
        if codes & {"asks_about_return", "asks_best_option", "compares_options"}:
            scores.update({"EID": max(scores.get("EID", 0.0), 0.20), "FORECAST": 0.20})
        return scores

    @staticmethod
    def _product_policy_item(item: ProductCatalogItem) -> ProductPolicyItem:
        return ProductPolicyItem(
            product_id=item.product_id,
            section=Section(item.section),
            is_active=item.is_active,
            rag_ready=item.rag_ready,
            compliance_flag=item.compliance_flag,
            restrictions=item.restrictions,
            base_risk_penalty=item.base_risk_penalty,
            base_friction_penalty=item.base_friction_penalty,
            metadata=item.metadata_json,
        )

    @staticmethod
    def _normalize_message(message: str) -> str:
        normalized = message.replace("ي", "ی").replace("ك", "ک")
        return re.sub(r"\s+", " ", normalized.strip())

    @staticmethod
    def _fingerprint(message, events, page):
        payload = {
            "message": message,
            "events": [item.model_dump(mode="json") for item in events],
            "page": page.model_dump(mode="json"),
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
