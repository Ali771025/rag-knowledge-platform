from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.conversation_memory.exceptions import DialogueManagerError
from app.conversation_memory.intent_detector import IntentDetector
from app.conversation_memory.models import ConversationContext, ConversationState
from app.conversation_memory.service import ConversationMemoryService
from app.internal.conversion.policy_enums import JourneyStage, TriggerType as PolicyTriggerType
from app.internal.conversion.rule_engine import (
    ConversionDecisionRuleEngine,
    ConversionDecisionRuleInput,
    ConversionDecisionRuleOutput,
)
from app.observability.event_emitter import AsyncEventEmitter
from app.observability.models import ConversionEvent
from app.observability.outcome_logger import OutcomeLogger
from app.prompt_orchestration.models import PromptOrchestrationMeta
from app.prompt_orchestration.trigger_template_resolver import TriggerTemplateError, TriggerTemplateResolver
from app.services.dialogue.service import (
    ConversionServiceHook,
    DialogueIntelligenceHooks,
    PersonaServiceHook,
    build_dialogue_orchestration_services,
)
from app.services.guardrails.dialogue_adapter import GuardrailsDialogueAdapter
from app.services.guardrails.models import Document
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class BaseDialogueManager(Protocol):
    """Abstract dialogue manager contract for response generation."""

    def generate_response(self, context: ConversationContext) -> tuple[str, dict]:
        """Generate assistant response text and optional metadata."""


class SimpleDialogueManager:
    """Deterministic fallback dialogue manager implementation."""

    _STATE_RESPONSES: dict[ConversationState, str] = {
        ConversationState.START: "Welcome! I can walk you through the onboarding process. Would you like a quick overview?",
        ConversationState.INTRO: "Great start. This onboarding helps you understand goals, structure, and what to do next.",
        ConversationState.EDUCATION: "Let's focus on learning. I can explain the core steps and expectations one by one.",
        ConversationState.QNA: "Ask me anything about the onboarding process, and I'll clarify it clearly.",
        ConversationState.JOIN: "You're ready to join. I can guide you through the final participation steps.",
    }

    def generate_response(self, context: ConversationContext) -> tuple[str, dict]:
        """Return deterministic state-based fallback response."""
        try:
            response = self._STATE_RESPONSES.get(
                context.state,
                self._STATE_RESPONSES[ConversationState.START],
            )
            attachments = context.metadata.get("attachments")
            if isinstance(attachments, list) and attachments:
                attachment_names = [
                    str(item.get("filename", "")).strip()
                    for item in attachments
                    if isinstance(item, dict) and str(item.get("filename", "")).strip()
                ]
                if attachment_names:
                    response = (
                        f"I received {len(attachment_names)} attachment(s): "
                        + ", ".join(attachment_names[:5])
                        + ". "
                        + response
                    )

            metadata = {
                "generator": "simple_fallback",
                "state": context.state.value,
                "rag_used": False,
                # TODO(phase-12+): Replace with RAG pipeline retrieval + grounding metadata.
                "todo_rag_integration": True,
            }
            return response, metadata
        except Exception as exc:  # pragma: no cover - defensive safety net
            logger.exception("Simple dialogue generation failed.")
            raise DialogueManagerError("Failed to generate fallback dialogue response.") from exc


class DialogueManager:
    """Compatibility facade that bridges memory service and response generation."""

    VALID_STATES = ("start", "intro", "education", "qna", "join")

    def __init__(
        self,
        llm_service: LLMService | None = None,
        memory_service: ConversationMemoryService | None = None,
        response_manager: BaseDialogueManager | None = None,
        intent_detector: IntentDetector | None = None,
        guardrails_adapter: GuardrailsDialogueAdapter | None = None,
        intelligence_hooks: DialogueIntelligenceHooks | None = None,
        conversion_decision_engine: ConversionDecisionRuleEngine | None = None,
        event_emitter: AsyncEventEmitter | None = None,
        outcome_logger: OutcomeLogger | None = None,
        trigger_template_resolver: TriggerTemplateResolver | None = None,
    ) -> None:
        # Kept for compatibility with existing constructor signature.
        self.llm_service = llm_service or LLMService()
        self.memory_service = memory_service or ConversationMemoryService()
        self.response_manager = response_manager or SimpleDialogueManager()
        self.intent_detector = intent_detector or IntentDetector()
        self.guardrails_adapter = guardrails_adapter or GuardrailsDialogueAdapter()
        self.conversion_decision_engine = conversion_decision_engine or ConversionDecisionRuleEngine()
        self.event_emitter = event_emitter or AsyncEventEmitter()
        self.outcome_logger = outcome_logger or OutcomeLogger()
        self.trigger_template_resolver = trigger_template_resolver or TriggerTemplateResolver()
        if intelligence_hooks is not None:
            self.intelligence_hooks = intelligence_hooks
        else:
            try:
                services = build_dialogue_orchestration_services()
                self.intelligence_hooks = DialogueIntelligenceHooks(
                    persona_hook=PersonaServiceHook(services.persona_service),
                    conversion_hook=ConversionServiceHook(services.conversion_service),
                )
            except Exception:  # pragma: no cover - hooks are optional
                logger.warning("Failed to bootstrap persona/conversion hooks; using no-op hooks.", exc_info=True)
                self.intelligence_hooks = DialogueIntelligenceHooks()

    def handle_message(
        self,
        db: Session,
        session_id: UUID,
        message: str,
        current_state: str,
    ) -> tuple[str, str, list[str]]:
        """Handle a user message and return assistant message + state + actions."""
        _ = db
        try:
            normalized_state = self._normalize_state(current_state)
            detected_intent = self.intent_detector.detect(message)
            intent_score = self._intent_score(detected_intent)
            orchestration_metadata = self._run_intelligence_hooks(
                session_id=str(session_id),
                message=message,
                state=normalized_state,
                intent=detected_intent,
            )

            pre_result = self.guardrails_adapter.run_pre_generation_safety(
                user_query=message,
                user_state=normalized_state,
                trace_id=str(session_id),
            )
            if not pre_result.is_allowed:
                return (
                    pre_result.fallback_response or self.guardrails_adapter.resolve_fallback_message(
                        fallback_key="low_confidence",
                        user_query=message,
                    ),
                    normalized_state,
                    self._build_actions(normalized_state, normalized_state),
                )

            context = ConversationContext(
                session_id=session_id,
                state=ConversationState(normalized_state),
                metadata={
                    "latest_user_message": message,
                    "orchestration": orchestration_metadata,
                    "intent": detected_intent,
                },
            )
            retrieved_docs = self._extract_retrieved_docs(context.metadata)
            if retrieved_docs:
                retrieval_result = self.guardrails_adapter.run_retrieval_validation(
                    user_query=message,
                    retrieved_docs=retrieved_docs,
                    user_state=normalized_state,
                )
                if not retrieval_result.is_valid:
                    return (
                        self.guardrails_adapter.resolve_fallback_message(
                            fallback_key=retrieval_result.fallback_action or "low_confidence",
                            user_query=message,
                        ),
                        normalized_state,
                        self._build_actions(normalized_state, normalized_state),
                    )

            assistant_message, _response_meta = self.response_manager.generate_response(context)
            safe_result = self.guardrails_adapter.run_post_generation_safety(
                user_query=message,
                retrieved_docs=retrieved_docs,
                llm_response=assistant_message,
                user_state=normalized_state,
                intent_score=intent_score,
                trace_id=str(session_id),
            )
            actions = self._build_actions(normalized_state, normalized_state)
            return safe_result.safe_response, normalized_state, actions
        except DialogueManagerError:
            raise
        except Exception as exc:  # pragma: no cover - defensive safety net
            logger.exception("Dialogue manager failed for session_id=%s", session_id)
            raise DialogueManagerError("Failed to handle dialogue message.") from exc

    def _normalize_state(self, state: str) -> str:
        """Normalize incoming state value."""
        return self.memory_service.state_machine.normalize_state(state)

    def _determine_next_state(self, state: str, message: str) -> str:
        """Determine next state placeholder."""
        _ = message
        return self.memory_service.state_machine.normalize_state(state)

    def _build_system_prompt(self, state: str) -> str:
        """Build system prompt placeholder."""
        _ = state
        return ""

    def _build_actions(self, old_state: str, new_state: str) -> list[str]:
        """Build action list placeholder."""
        if old_state == new_state:
            return [f"prompt:{new_state}"]
        return [f"transition:{old_state}->{new_state}", f"prompt:{new_state}"]

    def _extract_retrieved_docs(self, metadata: dict[str, object]) -> list[Document]:
        """Best-effort conversion of metadata docs into guardrails Document contracts."""
        raw_docs = metadata.get("retrieved_docs")
        if not isinstance(raw_docs, list):
            return []

        docs: list[Document] = []
        for item in raw_docs:
            if isinstance(item, Document):
                docs.append(item)
                continue
            if not isinstance(item, dict):
                continue

            content = item.get("content")
            if not isinstance(content, str) or not content.strip():
                continue

            score = item.get("score")
            score_value: float | None
            if isinstance(score, (int, float)):
                score_value = float(score)
            else:
                score_value = None

            metadata_value = item.get("metadata")
            if not isinstance(metadata_value, dict):
                metadata_value = {}

            doc_id = item.get("id")
            docs.append(
                Document(
                    id=str(doc_id) if doc_id is not None else None,
                    content=content,
                    score=score_value,
                    metadata={str(k): v for k, v in metadata_value.items()},
                )
            )

        return docs

    def _intent_score(self, intent: str) -> float:
        """Map coarse intent labels to a bounded deterministic confidence proxy."""
        intent_scores = {
            "ready": 0.85,
            "participate": 0.80,
            "join": 0.80,
            "start_learning": 0.75,
            "explain": 0.72,
            "tell_me_about": 0.70,
            "learn_more": 0.70,
            "ask_question": 0.68,
            "clarify": 0.62,
            "unknown": 0.60,
        }
        return intent_scores.get(intent, 0.60)

    def _run_intelligence_hooks(self, *, session_id: str, message: str, state: str, intent: str) -> dict[str, Any]:
        """Invoke optional persona/conversion hooks without affecting dialogue flow."""
        orchestration: dict[str, Any] = {}
        persona_hook = self.intelligence_hooks.persona_hook
        if persona_hook is not None:
            try:
                payload = persona_hook.on_message(session_id=session_id, message=message, state=state)
                if isinstance(payload, dict):
                    orchestration["persona"] = payload
            except Exception:  # pragma: no cover - hooks must not break dialogue flow
                logger.warning("persona hook failed for session_id=%s", session_id)

        conversion_hook = self.intelligence_hooks.conversion_hook
        if conversion_hook is not None:
            try:
                payload = conversion_hook.on_message(session_id=session_id, message=message, state=state)
                if isinstance(payload, dict):
                    orchestration["conversion"] = payload
            except Exception:  # pragma: no cover - hooks must not break dialogue flow
                logger.warning("conversion hook failed for session_id=%s", session_id)

        decision = self._evaluate_conversion_decision(orchestration=orchestration, intent=intent)
        orchestration["conversion_decision"] = decision.model_dump(mode="json")
        self._emit_conversion_decision_event_async(
            session_id=session_id,
            persona_payload=orchestration.get("persona") if isinstance(orchestration.get("persona"), dict) else {},
            conversion_payload=orchestration.get("conversion") if isinstance(orchestration.get("conversion"), dict) else {},
            decision=decision,
        )

        prompt_meta = self._build_prompt_orchestration_meta(orchestration=orchestration, decision=decision)
        if prompt_meta is not None:
            orchestration["prompt_orchestration_meta"] = prompt_meta.model_dump(mode="json")
        return orchestration

    def _evaluate_conversion_decision(self, *, orchestration: dict[str, Any], intent: str) -> ConversionDecisionRuleOutput:
        persona_payload = orchestration.get("persona") if isinstance(orchestration.get("persona"), dict) else {}
        conversion_payload = orchestration.get("conversion") if isinstance(orchestration.get("conversion"), dict) else {}

        persona_label = str(persona_payload.get("assigned_persona", "neutral"))
        confidence = self._resolve_persona_confidence(persona_payload)
        stage = self._resolve_journey_stage(conversion_payload.get("next_stage"))
        trust_score = self._safe_float(conversion_payload.get("updated_trust_score"), default=0.0)
        engagement_score = self._safe_float(
            (conversion_payload.get("orchestration_metadata") or {}).get("engagement_score")
            if isinstance(conversion_payload.get("orchestration_metadata"), dict)
            else None,
            default=0.0,
        )
        rejection_count = 0
        blocked_reasons = conversion_payload.get("blocked_reasons")
        if isinstance(blocked_reasons, list):
            rejection_count = len(blocked_reasons)

        try:
            return self.conversion_decision_engine.evaluate(
                ConversionDecisionRuleInput(
                    persona=persona_label,
                    confidence=confidence,
                    intent=intent,
                    stage=stage,
                    trust_score=trust_score,
                    engagement_score=engagement_score,
                    rejection_count=rejection_count,
                )
            )
        except Exception:
            logger.warning("conversion decision evaluation failed; using safe fallback", exc_info=True)
            return ConversionDecisionRuleOutput.safe_default("decision_engine_failure")

    def _build_prompt_orchestration_meta(
        self,
        *,
        orchestration: dict[str, Any],
        decision: ConversionDecisionRuleOutput,
    ) -> PromptOrchestrationMeta | None:
        conversion_payload = orchestration.get("conversion") if isinstance(orchestration.get("conversion"), dict) else {}
        primary_raw = conversion_payload.get("primary_trigger")
        secondary_raw = conversion_payload.get("secondary_trigger")
        if not isinstance(primary_raw, str):
            return None

        triggers: list[PolicyTriggerType] = []
        for raw in (primary_raw, secondary_raw):
            if not isinstance(raw, str) or not raw:
                continue
            token = raw.strip().lower()
            for trigger in PolicyTriggerType:
                if trigger.value == token:
                    if trigger not in triggers:
                        triggers.append(trigger)
                    break

        if not triggers:
            return None

        intensity = 0.5
        try:
            resolved = self.trigger_template_resolver.resolve(
                triggers=triggers,
                intensity=intensity,
                capacity_flags={},
            )
        except TriggerTemplateError:
            logger.warning("trigger template resolution failed", exc_info=True)
            return None

        resolved.conversion_decision = decision.model_dump(mode="json")
        return resolved

    def _emit_conversion_decision_event_async(
        self,
        *,
        session_id: str,
        persona_payload: dict[str, Any],
        conversion_payload: dict[str, Any],
        decision: ConversionDecisionRuleOutput,
    ) -> None:
        event = ConversionEvent(
            session_id=session_id,
            persona=str(persona_payload.get("assigned_persona", "neutral")),
            confidence=self._resolve_persona_confidence(persona_payload),
            modifiers=[
                str(item)
                for item in persona_payload.get("modifiers", [])
                if isinstance(item, str)
            ],
            stage=str(conversion_payload.get("next_stage", JourneyStage.ENTRY.value)),
            trust_score=self._safe_float(conversion_payload.get("updated_trust_score"), default=0.0),
            engagement_score=0.0,
            triggers_used=[
                trigger
                for trigger in (
                    self._resolve_trigger(conversion_payload.get("primary_trigger")),
                    self._resolve_trigger(conversion_payload.get("secondary_trigger")),
                )
                if trigger is not None
            ],
            cta_strength=decision.economic_suggestion_strength,
            cta_outcome="allowed" if decision.cta_allowed else "blocked",
            metadata={
                "event_name": "conversion_decision_evaluated",
                "matched_rules": decision.matched_rules,
                "allowed_actions": [item.value for item in decision.allowed_actions],
                "block_reason": decision.block_reason,
            },
        )
        self._dispatch_async(self.event_emitter.emit("conversion_decision_evaluated", event))
        self._dispatch_async(asyncio.to_thread(self.outcome_logger.log_conversion_outcome, event))

    @staticmethod
    def _resolve_persona_confidence(persona_payload: dict[str, Any]) -> float:
        scores = persona_payload.get("persona_scores")
        assigned = persona_payload.get("assigned_persona")
        if isinstance(scores, dict) and isinstance(assigned, str):
            raw = scores.get(assigned)
            if isinstance(raw, (int, float)):
                return max(0.0, min(1.0, float(raw)))
        return 0.0

    @staticmethod
    def _resolve_journey_stage(value: Any) -> JourneyStage:
        if isinstance(value, JourneyStage):
            return value
        if isinstance(value, str):
            token = value.strip().lower()
            for stage in JourneyStage:
                if stage.value == token:
                    return stage
        return JourneyStage.ENTRY

    @staticmethod
    def _resolve_trigger(value: Any) -> PolicyTriggerType | None:
        if isinstance(value, PolicyTriggerType):
            return value
        if isinstance(value, str):
            token = value.strip().lower()
            for trigger in PolicyTriggerType:
                if trigger.value == token:
                    return trigger
        return None

    @staticmethod
    def _safe_float(value: Any, *, default: float) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        return default

    @staticmethod
    def _dispatch_async(coro: Any) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            threading.Thread(
                target=lambda: asyncio.run(coro),
                daemon=True,
                name="conversion-decision-event-emitter",
            ).start()
