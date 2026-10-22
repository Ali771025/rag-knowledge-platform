"""Async orchestration service for conversation memory workflow."""

from __future__ import annotations

import asyncio
import logging
from time import perf_counter
from datetime import datetime, timezone
from typing import Any, Callable, Protocol
from uuid import UUID, uuid4

from app.core.database import SessionLocal
from app.core.config import settings
from app.core.runtime_services import RuntimeServices, get_runtime_services
from app.conversation_memory.context_manager import ConversationContextManager, build_context as default_build_context
from app.conversation_memory.exceptions import (
    ContextBuildError,
    DialogueManagerError,
    IntentDetectionError,
    MemoryPolicyError,
    PostgresRepositoryError,
    RedisRepositoryError,
    SessionNotFoundError,
)
from app.conversation_memory.intent_detector import BaseIntentDetector, RuleBasedIntentDetector
from app.conversation_memory.memory_policy import MemoryPolicy
from app.conversation_memory.models import (
    ConversationContext,
    ConversationMemoryDecision,
    ConversationRole,
    ConversationState,
    ConversationTraceMetadata,
    ConversationTurn,
    ResponseGenerationMetadata,
    ServiceResponse,
    SessionState,
)
from app.conversation_memory.postgres_repository import PostgresConversationRepository
from app.conversation_memory.redis_repository import RedisConversationRepository
from app.conversation_memory.serializers import serialize_user_profile
from app.conversation_memory.session_manager import ConversationSessionManager
from app.conversation_memory.state_machine import ConversationStateMachine, next_state as resolve_next_state
from app.internal.conversion.orchestration_models import ConversionFunnelRequest, ConversionFunnelResponse
from app.internal.conversion.policy_enums import CTAAction, CTAOutcome, ConversionOutcome, EconomicSuggestionStrength, JourneyStage
from app.internal.persona.orchestration_models import PersonaIntelligenceRequest, PersonaIntelligenceResponse
from app.models.llm.contracts import LLMRequest, LLMResponse, ProviderUsageRecord
from app.observability.event_emitter import AsyncEventEmitter
from app.observability.models import ConversionEvent
from app.observability.outcome_logger import OutcomeLogger
from app.rag.constants import REFUSAL_MESSAGE
from app.services.referral_intelligence_service import (
    ReferralIntelligenceDomainError,
    ReferralIntelligenceService,
    ReferralLinkNotFoundError,
)

logger = logging.getLogger(__name__)


class _DialogueGenerator(Protocol):
    def generate_response(self, context: ConversationContext) -> tuple[str, dict]:
        """Generate assistant response and metadata."""


class _PersonaOrchestrator(Protocol):
    async def analyze(self, request: PersonaIntelligenceRequest) -> PersonaIntelligenceResponse:
        """Run persona orchestration pipeline."""


class _ConversionOrchestrator(Protocol):
    async def update(self, request: ConversionFunnelRequest) -> ConversionFunnelResponse:
        """Run conversion funnel orchestration pipeline."""


class ConversationMemoryService:
    """Coordinates session, intent, state, context, and response generation workflow."""

    def __init__(
        self,
        *,
        session_manager: ConversationSessionManager | None = None,
        redis_repository: RedisConversationRepository | None = None,
        postgres_repository: PostgresConversationRepository | None = None,
        intent_detector: BaseIntentDetector | None = None,
        dialogue_manager: _DialogueGenerator | None = None,
        context_builder: Callable[[SessionState, str, int], ConversationContext] | None = None,
        context_manager: ConversationContextManager | None = None,
        state_machine: ConversationStateMachine | None = None,
        memory_policy: MemoryPolicy | None = None,
        persona_service: _PersonaOrchestrator | None = None,
        conversion_service: _ConversionOrchestrator | None = None,
        max_turns: int = 10,
        ttl_seconds: int = 86_400,
        runtime_services: RuntimeServices | None = None,
        event_emitter: AsyncEventEmitter | None = None,
        outcome_logger: OutcomeLogger | None = None,
    ) -> None:
        self.session_manager = session_manager or ConversationSessionManager()
        self.redis_repository = redis_repository or RedisConversationRepository()
        self.postgres_repository = postgres_repository or PostgresConversationRepository()
        self.intent_detector = intent_detector or RuleBasedIntentDetector()
        self.context_manager = context_manager or ConversationContextManager()
        self.context_builder = context_builder or default_build_context
        self.state_machine = state_machine or ConversationStateMachine()
        self.memory_policy = memory_policy or MemoryPolicy()
        self.max_turns = max_turns
        self.ttl_seconds = ttl_seconds
        self.runtime_services = runtime_services or get_runtime_services()
        self.event_emitter = event_emitter or AsyncEventEmitter()
        self.outcome_logger = outcome_logger or OutcomeLogger()
        self.feature_cache_orchestration_enabled = bool(getattr(settings, "feature_cache_orchestration_enabled", False))
        self.feature_model_routing_enabled = bool(getattr(settings, "feature_model_routing_enabled", False))
        self.feature_unified_llm_client_enabled = bool(getattr(settings, "feature_unified_llm_client_enabled", False))
        self.feature_fallback_enabled = bool(getattr(settings, "feature_fallback_enabled", False))
        self.feature_cost_tracking_enabled = bool(getattr(settings, "feature_cost_tracking_enabled", False))
        self.feature_budget_guard_enabled = bool(getattr(settings, "feature_budget_guard_enabled", False))
        self.feature_shadow_routing_enabled = bool(getattr(settings, "feature_shadow_routing_enabled", False))
        self.feature_observability_adapters_enabled = bool(
            getattr(settings, "feature_observability_adapters_enabled", True)
        )
        if dialogue_manager is None:
            # Late import avoids circular import with app.services.dialogue_manager -> this module.
            from app.services.dialogue_manager import SimpleDialogueManager

            self.dialogue_manager: _DialogueGenerator = SimpleDialogueManager()
        else:
            self.dialogue_manager = dialogue_manager

        if persona_service is not None and conversion_service is not None:
            self.persona_service = persona_service
            self.conversion_service = conversion_service
        else:
            try:
                from app.services.dialogue.service import build_dialogue_orchestration_services

                services = build_dialogue_orchestration_services()
                self.persona_service = services.persona_service
                self.conversion_service = services.conversion_service
            except Exception:  # pragma: no cover - orchestration is optional and must degrade safely
                logger.exception("persona_conversion_orchestration.bootstrap_failed")
                self.persona_service = None
                self.conversion_service = None

    async def handle_user_message(
        self,
        session_id: str | None,
        user_id: str | None,
        message: str,
        knowledge_labels: list[str] | None = None,
        memory_scope: str | None = None,
        referral_invite_code: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> ServiceResponse:
        """Run the full conversation memory workflow for an incoming user message."""
        started_at = datetime.now(timezone.utc)
        warnings: list[str] = []
        degraded = False
        timestamps: dict[str, str] = {"received_at": started_at.isoformat()}
        trace_id = self._build_trace_id()

        if not isinstance(message, str):
            return ServiceResponse(
                success=False,
                message="Message cannot be empty.",
                error_code="invalid_message",
                data={"warnings": warnings},
                timestamp=started_at,
            )

        stripped_message = message.strip()
        normalized_attachments = self._normalize_attachments(attachments)
        if not stripped_message and not normalized_attachments:
            return ServiceResponse(
                success=False,
                message="Message cannot be empty.",
                error_code="invalid_message",
                data={"warnings": warnings},
                timestamp=started_at,
            )

        effective_user_message = self._merge_message_with_attachments(
            message=stripped_message,
            attachments=normalized_attachments,
        )
        normalized_labels = self._normalize_label_scope(knowledge_labels)
        normalized_scope = self._normalize_memory_scope(memory_scope)
        normalized_referral_invite_code = self._normalize_referral_invite_code(referral_invite_code)

        # 1) load existing session or create new session
        bootstrap_metadata: dict[str, str] = {}
        if normalized_referral_invite_code:
            bootstrap_metadata["referral_invite_code"] = normalized_referral_invite_code
        bootstrap_input = {
            "message": stripped_message,
            "pre_engagement": "first_message",
            "time_of_day": self._time_of_day_bucket(started_at.hour),
            "referral_link_type": "customized_invite" if normalized_referral_invite_code else None,
            "metadata": bootstrap_metadata,
        }
        try:
            session_state = await asyncio.to_thread(
                self._get_or_create_session_compat,
                session_id,
                user_id,
                bootstrap_input,
            )
        except RedisRepositoryError as exc:
            logger.warning(
                "session.bootstrap_degraded session_id=%s user_id=%s error=%s",
                session_id,
                user_id,
                type(exc).__name__,
            )
            warnings.append("redis_session_bootstrap_failed")
            degraded = True
            session_state = self._build_ephemeral_session_state(
                user_id=user_id,
                bootstrap_input=bootstrap_input,
            )
        except SessionNotFoundError as exc:
            logger.exception(
                "session.bootstrap_failed session_id=%s user_id=%s error=%s",
                session_id,
                user_id,
                type(exc).__name__,
            )
            return ServiceResponse(
                success=False,
                message="Failed to initialize conversation session.",
                error_code="session_bootstrap_failed",
                data={"warnings": warnings, "degraded": False, "critical_failure": True},
                timestamp=started_at,
            )

        resolved_session_id = str(session_state.session_id)
        resolved_user_id = self._resolve_user_id(session_state=session_state, fallback_user_id=user_id)
        referral_agent_context: dict[str, Any] | None = None
        if normalized_referral_invite_code:
            try:
                session_state, referral_agent_context = await asyncio.to_thread(
                    self._attach_referral_agent_context,
                    session_state,
                    normalized_referral_invite_code,
                    resolved_user_id,
                )
                if referral_agent_context is not None:
                    try:
                        await self.redis_repository.update_session(session_state, ttl_seconds=self.ttl_seconds)
                    except RedisRepositoryError:
                        warnings.append("redis_referral_context_update_failed")
                        degraded = True
                else:
                    warnings.append("referral_context_requires_authenticated_invitee")
            except ReferralLinkNotFoundError:
                warnings.append("referral_context_not_authorized")
            except ReferralIntelligenceDomainError:
                warnings.append("referral_context_unavailable")
            except Exception:
                logger.warning(
                    "referral.context_hydration_failed session_id=%s invite_code=%s",
                    resolved_session_id,
                    normalized_referral_invite_code,
                    exc_info=True,
                )
                warnings.append("referral_context_hydration_failed")
                degraded = True
        entry_context = session_state.metadata.get("entry_context")
        if not isinstance(entry_context, dict):
            entry_context = {}
        previous_state = session_state.state
        session_state = self._merge_scope_metadata(
            session_state=session_state,
            knowledge_labels=normalized_labels,
            memory_scope=normalized_scope,
        )
        timestamps["session_resolved_at"] = datetime.now(timezone.utc).isoformat()

        # 2) optionally load user profile from PostgreSQL if missing
        try:
            profile_exists = bool(session_state.metadata.get("user_profile"))
            if not profile_exists and resolved_user_id:
                profile = await self.postgres_repository.get_user_profile(resolved_user_id)
                if profile is not None:
                    metadata = dict(session_state.metadata or {})
                    metadata["user_profile"] = serialize_user_profile(profile)
                    session_state = session_state.model_copy(
                        update={"metadata": metadata, "updated_at": datetime.now(timezone.utc)},
                        deep=True,
                    )
                    try:
                        await self.redis_repository.update_session(session_state, ttl_seconds=self.ttl_seconds)
                    except RedisRepositoryError:
                        warnings.append("redis_profile_cache_update_failed")
                        degraded = True
        except PostgresRepositoryError as exc:
            logger.warning(
                "profile.load_non_critical_failure session_id=%s user_id=%s error=%s",
                resolved_session_id,
                resolved_user_id,
                type(exc).__name__,
            )
            warnings.append("profile_load_failed")
            degraded = True

        # 4) detect intent (before persisting user turn so it can be enriched)
        try:
            intent = self.intent_detector.detect_intent(stripped_message, session_state=session_state)
        except IntentDetectionError as exc:
            logger.warning(
                "intent.detect_non_critical_failure session_id=%s error=%s",
                resolved_session_id,
                type(exc).__name__,
            )
            warnings.append("intent_detection_failed")
            degraded = True
            intent = "unknown"

        # 3) analyze persona + conversion funnel orchestration (graceful fallback on failures)
        persona_result: PersonaIntelligenceResponse | None = None
        conversion_result: ConversionFunnelResponse | None = None
        if self.persona_service is not None:
            try:
                persona_metadata = {
                    "follow_up_count": 1,
                    "messages_in_session": len(self._extract_turns(session_state)),
                    "intent_events": 1,
                    "entry_context": entry_context,
                }
                persona_result = await self.persona_service.analyze(
                    PersonaIntelligenceRequest(
                        session_id=resolved_session_id,
                        user_id=resolved_user_id,
                        message=stripped_message,
                        metadata=persona_metadata,
                        recent_messages=self._extract_recent_user_messages(session_state),
                    )
                )
                timestamps["persona_analyzed_at"] = datetime.now(timezone.utc).isoformat()
            except Exception as exc:  # pragma: no cover - defensive fallback
                logger.warning(
                    "persona.orchestration_non_critical_failure session_id=%s error=%s",
                    resolved_session_id,
                    type(exc).__name__,
                )
                warnings.append("persona_analysis_failed")
                degraded = True

        if self.conversion_service is not None:
            try:
                persona_label = (
                    persona_result.assigned_persona.value
                    if persona_result is not None
                    else "explorer"
                )
                persona_confidence = (
                    max(0.0, min(1.0, persona_result.confidence_gap))
                    if persona_result is not None
                    else 0.0
                )
                current_funnel_stage = self._extract_funnel_stage(session_state)
                trust_score = self._extract_trust_score(session_state)

                conversion_result = await self.conversion_service.update(
                    ConversionFunnelRequest(
                        session_id=resolved_session_id,
                        user_id=resolved_user_id,
                        persona_label=persona_label,
                        persona_confidence=persona_confidence,
                        trust_score=trust_score,
                        current_stage=current_funnel_stage,
                        intent=intent,
                        repeated_interaction_count=1,
                        clarification_success_count=1 if "clarify" in intent else 0,
                        objection_count=1 if "objection" in intent else 0,
                        confusion_count=1 if "unknown" == intent else 0,
                        metadata={"entry_context": entry_context},
                    )
                )
                timestamps["conversion_updated_at"] = datetime.now(timezone.utc).isoformat()
            except Exception as exc:  # pragma: no cover - defensive fallback
                logger.warning(
                    "conversion.orchestration_non_critical_failure session_id=%s error=%s",
                    resolved_session_id,
                    type(exc).__name__,
                )
                warnings.append("conversion_update_failed")
                degraded = True

        orchestration_metadata = self._build_orchestration_metadata(
            persona_result=persona_result,
            conversion_result=conversion_result,
        )
        orchestration_metadata["entry_context"] = entry_context
        if referral_agent_context is not None:
            orchestration_metadata["referral_agent_context"] = referral_agent_context

        # 5) compute next state using state machine
        next_state = resolve_next_state(session_state.state, intent)
        timestamps["state_computed_at"] = datetime.now(timezone.utc).isoformat()

        # 6) update session state if changed
        if next_state != session_state.state:
            session_state = session_state.model_copy(
                update={"state": next_state, "updated_at": datetime.now(timezone.utc)},
                deep=True,
            )
            try:
                await self.redis_repository.update_session(session_state, ttl_seconds=self.ttl_seconds)
            except RedisRepositoryError:
                warnings.append("redis_state_update_failed")
                degraded = True
        timestamps["state_updated_at"] = datetime.now(timezone.utc).isoformat()

        # 7) apply memory policy if needed
        memory_policy_actions: list[str] = []
        try:
            policy_before = session_state.model_copy(deep=True)
            session_state = self.memory_policy.apply_memory_policy(session_state, max_turns=self.max_turns)
            policy_decision = ConversationMemoryDecision(
                next_state=session_state.state,
                should_persist=True,
                actions=self._derive_memory_policy_actions(policy_before=policy_before, policy_after=session_state),
            )
            memory_policy_actions = list(policy_decision.actions)
            try:
                await self.redis_repository.update_session(session_state, ttl_seconds=self.ttl_seconds)
            except RedisRepositoryError:
                warnings.append("redis_memory_policy_persist_failed")
                degraded = True
        except MemoryPolicyError as exc:
            logger.warning(
                "memory_policy.non_critical_failure session_id=%s error=%s",
                resolved_session_id,
                type(exc).__name__,
            )
            warnings.append("memory_policy_failed")
            degraded = True
            memory_policy_actions = ["memory_policy_failed"]
        timestamps["memory_policy_applied_at"] = datetime.now(timezone.utc).isoformat()

        turn_base_meta = {
            "trace_id": trace_id,
            "detected_intent": intent,
            "previous_state": previous_state.value,
            "new_state": session_state.state.value,
            "state_transition": f"{previous_state.value}->{session_state.state.value}",
            "attachment_count": len(normalized_attachments),
            "memory_policy_actions": list(memory_policy_actions),
            "timestamps": dict(timestamps),
        }

        user_turn = ConversationTurn(
            role=ConversationRole.USER,
            message=stripped_message or "Please review the attached files.",
            timestamp=datetime.now(timezone.utc),
            metadata={
                **turn_base_meta,
                "intent": intent,
                "attachments": normalized_attachments,
            },
        )

        # 3) append user turn
        try:
            session_state = await self.redis_repository.append_turn(
                session_id=resolved_session_id,
                turn=user_turn,
                ttl_seconds=self.ttl_seconds,
            )
        except (RedisRepositoryError, SessionNotFoundError) as exc:
            logger.error(
                "session.append_user_turn_critical_failure session_id=%s error=%s",
                resolved_session_id,
                type(exc).__name__,
            )
            warnings.append("redis_user_turn_append_failed")
            degraded = True
            session_state = self._append_turn_locally(session_state, user_turn)

        # 8) build context
        try:
            context = self.context_builder(session_state, effective_user_message, self.max_turns)
        except ContextBuildError as exc:
            logger.warning(
                "context.build_non_critical_failure session_id=%s error=%s",
                resolved_session_id,
                type(exc).__name__,
            )
            warnings.append("context_build_failed")
            degraded = True
            context = ConversationContext(
                session_id=session_state.session_id,
                state=session_state.state,
                metadata={"latest_user_message": effective_user_message, "fallback_context": True},
            )
        context_metadata = dict(context.metadata or {})
        context_metadata["orchestration"] = orchestration_metadata
        if normalized_labels:
            context_metadata["knowledge_labels"] = list(normalized_labels)
        if normalized_scope:
            context_metadata["memory_scope"] = normalized_scope
        if referral_agent_context is not None:
            context_metadata["referral_agent_context"] = referral_agent_context
        if normalized_attachments:
            context_metadata["attachments"] = normalized_attachments
        context = context.model_copy(update={"metadata": context_metadata}, deep=True)
        timestamps["context_built_at"] = datetime.now(timezone.utc).isoformat()
        is_conversational_turn = self._is_pure_conversational_turn(message=stripped_message, intent=intent)

        # 9) generate response (advanced routed stack or deterministic fallback)
        response_generation_meta = ResponseGenerationMetadata(generator="unknown", rag_used=False, details={})
        try:
            if is_conversational_turn:
                assistant_message, assistant_metadata = await asyncio.to_thread(
                    self.dialogue_manager.generate_response,
                    context,
                )
                assistant_metadata = {
                    **dict(assistant_metadata or {}),
                    "generator": str(dict(assistant_metadata or {}).get("generator", "simple_dialogue")),
                    "rag_used": False,
                }
            else:
                try:
                    assistant_message, assistant_metadata = await asyncio.to_thread(
                        self._run_rag_orchestrator,
                        message=effective_user_message,
                        context=context,
                    )
                except Exception as exc:
                    logger.warning(
                        "rag_generation_failed session_id=%s error=%s",
                        resolved_session_id,
                        type(exc).__name__,
                    )
                    warnings.append("rag_generation_failed")
                    degraded = True
                    assistant_message = REFUSAL_MESSAGE
                    assistant_metadata = {
                        "generator": "rag_orchestrator_refusal_fallback",
                        "rag_used": True,
                        "grounding_status": "insufficient_evidence",
                    }

            response_generation_meta = ResponseGenerationMetadata(
                generator=str(assistant_metadata.get("generator", "unknown")),
                rag_used=bool(assistant_metadata.get("rag_used", False)),
                model_name=assistant_metadata.get("model"),
                latency_ms=assistant_metadata.get("latency_ms")
                if isinstance(assistant_metadata.get("latency_ms"), int)
                else None,
                details=dict(assistant_metadata),
            )
        except DialogueManagerError as exc:
            logger.warning(
                "dialogue.generate_non_critical_failure session_id=%s error=%s",
                resolved_session_id,
                type(exc).__name__,
            )
            warnings.append("dialogue_generation_failed")
            degraded = True
            assistant_message = (
                "I am sorry, I am having trouble generating a response right now. "
                "Please try again in a moment."
            )
            assistant_metadata = {"generator": "emergency_fallback", "rag_used": False}
            response_generation_meta = ResponseGenerationMetadata(
                generator="emergency_fallback",
                rag_used=False,
                details=dict(assistant_metadata),
            )
        except Exception:  # pragma: no cover - defensive fallback
            logger.exception("dialogue.generate_unexpected session_id=%s", resolved_session_id)
            warnings.append("dialogue_generation_unexpected_failure")
            degraded = True
            assistant_message = "I am unable to respond right now."
            assistant_metadata = {"generator": "emergency_fallback", "rag_used": False}
            response_generation_meta = ResponseGenerationMetadata(
                generator="emergency_fallback",
                rag_used=False,
                details=dict(assistant_metadata),
            )
        timestamps["response_generated_at"] = datetime.now(timezone.utc).isoformat()

        await self._track_standard_chat_token_usage(
            session_id=resolved_session_id,
            user_id=resolved_user_id,
            message=effective_user_message,
            assistant_message=assistant_message,
            assistant_metadata=assistant_metadata,
            trace_id=trace_id,
            started_at=started_at,
        )

        # 10) append assistant turn
        assistant_turn = ConversationTurn(
            role=ConversationRole.ASSISTANT,
            message=assistant_message,
            timestamp=datetime.now(timezone.utc),
            metadata={
                **turn_base_meta,
                "intent": intent,
                "response_generation": response_generation_meta.model_dump(mode="json"),
                "orchestration": orchestration_metadata,
                **assistant_metadata,
            },
        )
        try:
            session_state = await self.redis_repository.append_turn(
                session_id=resolved_session_id,
                turn=assistant_turn,
                ttl_seconds=self.ttl_seconds,
            )
        except (RedisRepositoryError, SessionNotFoundError) as exc:
            logger.error(
                "session.append_assistant_turn_critical_failure session_id=%s error=%s",
                resolved_session_id,
                type(exc).__name__,
            )
            warnings.append("redis_assistant_turn_append_failed")
            degraded = True
            session_state = self._append_turn_locally(session_state, assistant_turn)
        timestamps["assistant_turn_appended_at"] = datetime.now(timezone.utc).isoformat()

        # 11) persist updated session to Redis
        try:
            await self.redis_repository.update_session(session_state, ttl_seconds=self.ttl_seconds)
        except RedisRepositoryError as exc:
            logger.error(
                "session.persist_critical_failure session_id=%s error=%s",
                resolved_session_id,
                type(exc).__name__,
            )
            warnings.append("redis_persist_failed")
            degraded = True
        timestamps["redis_persist_attempted_at"] = datetime.now(timezone.utc).isoformat()

        # 12) log both turns to PostgreSQL
        try:
            await self.postgres_repository.save_conversation_turn(
                session_id=resolved_session_id,
                user_id=resolved_user_id,
                role=user_turn.role.value,
                message=user_turn.message,
                timestamp=user_turn.timestamp,
                metadata=user_turn.metadata,
            )
            await self.postgres_repository.save_conversation_turn(
                session_id=resolved_session_id,
                user_id=resolved_user_id,
                role=assistant_turn.role.value,
                message=assistant_turn.message,
                timestamp=assistant_turn.timestamp,
                metadata=assistant_turn.metadata,
            )
        except PostgresRepositoryError as exc:
            logger.warning(
                "db.turn_logging_non_critical_failure session_id=%s error=%s",
                resolved_session_id,
                type(exc).__name__,
            )
            warnings.append("db_turn_logging_failed")
            degraded = True
        timestamps["db_turn_logging_attempted_at"] = datetime.now(timezone.utc).isoformat()

        # 13) persist session metadata if useful
        trace_metadata = ConversationTraceMetadata(
            trace_id=trace_id,
            detected_intent=intent,
            previous_state=previous_state,
            new_state=session_state.state,
            memory_policy_actions=list(memory_policy_actions),
            timestamps=dict(timestamps),
            response_generation=response_generation_meta,
        )
        session_meta = {
            "conversation_memory": {
                "last_intent": intent,
                "last_state": session_state.state.value,
                "state_transition": f"{previous_state.value}->{session_state.state.value}",
                "last_response_generator": assistant_metadata.get("generator", "unknown"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "memory_policy_actions": list(memory_policy_actions),
                "trace": trace_metadata.model_dump(mode="json"),
            }
        }
        try:
            if resolved_user_id:
                await self.postgres_repository.save_session_metadata(
                    session_id=resolved_session_id,
                    user_id=resolved_user_id,
                    metadata=session_meta,
                )
        except PostgresRepositoryError as exc:
            logger.warning(
                "db.session_metadata_non_critical_failure session_id=%s error=%s",
                resolved_session_id,
                type(exc).__name__,
            )
            warnings.append("db_session_metadata_failed")
            degraded = True
        timestamps["session_metadata_persist_attempted_at"] = datetime.now(timezone.utc).isoformat()

        self._emit_outcome_event_non_blocking(
            session_id=resolved_session_id,
            user_id=resolved_user_id,
            persona_result=persona_result,
            conversion_result=conversion_result,
        )

        # 14) return ServiceResponse
        actions = self.state_machine.build_actions(
            old_state=previous_state.value,
            new_state=session_state.state.value,
        )
        response_data = {
            "session_id": resolved_session_id,
            "user_id": resolved_user_id,
            "intent": intent,
            "previous_state": previous_state.value,
            "next_state": session_state.state.value,
            "assistant_metadata": assistant_metadata,
            "response_generation": response_generation_meta.model_dump(mode="json"),
            "memory_policy_actions": list(memory_policy_actions),
            "trace_id": trace_id,
            "timestamps": dict(timestamps),
            "orchestration": orchestration_metadata,
            "knowledge_labels": list(normalized_labels),
            "memory_scope": normalized_scope,
            "referral_invite_code": normalized_referral_invite_code,
            "referral_agent_context_attached": referral_agent_context is not None,
            "attachments": normalized_attachments,
            "warnings": warnings,
            "degraded": degraded,
            "critical_failures": [
                code
                for code in warnings
                if code.startswith("redis_") and ("append" in code or "persist" in code)
            ],
        }
        logger.info(
            "conversation_message_handled session_id=%s user_id=%s trace_id=%s intent=%s transition=%s->%s warnings=%s degraded=%s",
            resolved_session_id,
            resolved_user_id,
            trace_id,
            intent,
            previous_state.value,
            session_state.state.value,
            len(warnings),
            degraded,
        )
        return ServiceResponse(
            success=True,
            message=assistant_message,
            state=session_state.state,
            actions=actions,
            context=context,
            data=response_data,
            timestamp=datetime.now(timezone.utc),
        )

    def _merge_scope_metadata(
        self,
        *,
        session_state: SessionState,
        knowledge_labels: list[str],
        memory_scope: str | None,
    ) -> SessionState:
        metadata = dict(session_state.metadata or {})
        metadata.setdefault("rag_scope", {})
        rag_scope = metadata["rag_scope"] if isinstance(metadata["rag_scope"], dict) else {}
        rag_scope["knowledge_labels"] = list(knowledge_labels)
        if memory_scope:
            rag_scope["memory_scope"] = memory_scope
        metadata["rag_scope"] = rag_scope
        return session_state.model_copy(update={"metadata": metadata}, deep=True)

    def _attach_referral_agent_context(
        self,
        session_state: SessionState,
        referral_invite_code: str,
        resolved_user_id: str | None,
    ) -> tuple[SessionState, dict[str, Any] | None]:
        if not resolved_user_id:
            return session_state, None

        try:
            current_user_id = UUID(str(resolved_user_id))
        except ValueError:
            return session_state, None

        with SessionLocal() as db:
            agent_context = ReferralIntelligenceService().get_agent_context_by_invite_code(
                db,
                invite_code=referral_invite_code,
                current_user_id=current_user_id,
                metadata={"access_path": "conversation_memory_bootstrap"},
            )

        context_payload = agent_context.model_dump(mode="json")
        metadata = dict(session_state.metadata or {})
        metadata["referral_invite_code"] = referral_invite_code
        metadata["referral_agent_context"] = context_payload

        entry_context = metadata.get("entry_context")
        if not isinstance(entry_context, dict):
            entry_context = {}
        entry_context = dict(entry_context)
        entry_context["referral_agent_context"] = context_payload
        entry_context["referral_agent_context_source"] = "referrer_reported"
        entry_context["referral_agent_context_truth_status"] = "unverified_referrer_signal"
        entry_context["weak_bias_only"] = True
        metadata["entry_context"] = entry_context

        return (
            session_state.model_copy(
                update={"metadata": metadata, "updated_at": datetime.now(timezone.utc)},
                deep=True,
            ),
            context_payload,
        )

    @staticmethod
    def _normalize_label_scope(labels: list[str] | None) -> list[str]:
        if not labels:
            return []
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in labels:
            label = " ".join(str(raw or "").strip().split()).lower()
            if not label or label in seen:
                continue
            seen.add(label)
            normalized.append(label)
        return normalized

    @staticmethod
    def _normalize_memory_scope(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split()).lower()
        return normalized or None

    @staticmethod
    def _normalize_referral_invite_code(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split()).upper()
        return normalized or None

    @staticmethod
    def _normalize_attachments(attachments: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        if not attachments:
            return []
        normalized: list[dict[str, Any]] = []
        for raw in attachments:
            if not isinstance(raw, dict):
                continue
            filename = " ".join(str(raw.get("filename", "")).split()).strip()
            if not filename:
                continue
            content_type = " ".join(str(raw.get("content_type", "")).split()).strip().lower() or None
            kind = " ".join(str(raw.get("kind", "binary")).split()).strip().lower() or "binary"
            extracted = str(raw.get("extracted_text", "") or "").strip()
            try:
                size_bytes = max(0, int(raw.get("size_bytes", 0) or 0))
            except Exception:
                size_bytes = 0
            normalized.append(
                {
                    "filename": filename[:255],
                    "content_type": content_type,
                    "kind": kind,
                    "extracted_text": extracted[:12_000] if extracted else None,
                    "size_bytes": size_bytes,
                }
            )
        return normalized

    @staticmethod
    def _merge_message_with_attachments(*, message: str, attachments: list[dict[str, Any]]) -> str:
        base = message.strip()
        if not attachments:
            return base

        chunks: list[str] = []
        for index, attachment in enumerate(attachments, start=1):
            name = str(attachment.get("filename", "attachment")).strip() or f"attachment-{index}"
            kind = str(attachment.get("kind", "binary")).strip() or "binary"
            content_type = str(attachment.get("content_type", "")).strip()
            extracted_text = str(attachment.get("extracted_text", "") or "").strip()
            header = f"[Attachment {index}] name={name}; kind={kind}; content_type={content_type or 'unknown'}"
            if extracted_text:
                chunks.append(f"{header}\n{extracted_text}")
            else:
                chunks.append(f"{header}\nNo extracted text content was available.")

        prefix = base if base else "Please analyze the attached files."
        return f"{prefix}\n\nAttached file context:\n" + "\n\n".join(chunks)

    @staticmethod
    def _extract_turns(session_state: SessionState) -> list[dict[str, Any]]:
        metadata = dict(session_state.metadata or {})
        turns = metadata.get("turns", [])
        if not isinstance(turns, list):
            return []
        return [item for item in turns if isinstance(item, dict)]

    def _extract_recent_user_messages(self, session_state: SessionState, limit: int = 2) -> list[str]:
        turns = self._extract_turns(session_state)
        messages: list[str] = []
        for item in turns:
            role = str(item.get("role", "")).strip().lower()
            message = item.get("message")
            if role == ConversationRole.USER.value and isinstance(message, str) and message.strip():
                messages.append(message.strip())
        return messages[-limit:]

    @staticmethod
    def _extract_funnel_stage(session_state: SessionState) -> JourneyStage:
        metadata = dict(session_state.metadata or {})
        orchestration = metadata.get("orchestration")
        if isinstance(orchestration, dict):
            conversion = orchestration.get("conversion")
            if isinstance(conversion, dict):
                stage = str(conversion.get("next_stage", "")).strip().lower()
                try:
                    return JourneyStage(stage)
                except ValueError:
                    pass
        return JourneyStage.ENTRY

    @staticmethod
    def _extract_trust_score(session_state: SessionState) -> float:
        metadata = dict(session_state.metadata or {})
        orchestration = metadata.get("orchestration")
        if isinstance(orchestration, dict):
            conversion = orchestration.get("conversion")
            if isinstance(conversion, dict):
                score = conversion.get("updated_trust_score")
                if isinstance(score, (int, float)):
                    return min(1.0, max(0.0, float(score)))
        return 0.25

    @staticmethod
    def _build_orchestration_metadata(
        *,
        persona_result: PersonaIntelligenceResponse | None,
        conversion_result: ConversionFunnelResponse | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if persona_result is not None:
            payload["persona"] = persona_result.model_dump(mode="json")
        if conversion_result is not None:
            payload["conversion"] = conversion_result.model_dump(mode="json")
        return payload

    def _advanced_pipeline_enabled(self) -> bool:
        return (
            self.feature_cache_orchestration_enabled
            and self.feature_model_routing_enabled
            and self.feature_unified_llm_client_enabled
        )

    @staticmethod
    def _is_pure_conversational_turn(*, message: str, intent: str) -> bool:
        normalized_message = " ".join(str(message or "").strip().lower().split())
        if not normalized_message:
            return True
        if intent == "greeting":
            return True
        conversational_phrases = {
            "thanks",
            "thank you",
            "ok",
            "okay",
            "got it",
            "cool",
            "bye",
            "goodbye",
        }
        if normalized_message in conversational_phrases:
            return True
        return False

    def _run_rag_orchestrator(
        self,
        *,
        message: str,
        context: ConversationContext,
    ) -> tuple[str, dict[str, Any]]:
        from app.rag.rag_orchestrator import RAGOrchestrator, RAGOrchestratorInput

        labels_raw = context.metadata.get("knowledge_labels")
        labels = [str(item).strip().lower() for item in labels_raw if str(item).strip()] if isinstance(labels_raw, list) else []
        filters: dict[str, Any] | None = None
        metadata: dict[str, Any] = {}
        if labels:
            filters = {
                "labels": labels,
                "label": labels[0],
                "qdrant": {"must": [{"key": "label", "match": {"any": labels}}]},
            }
            metadata["knowledge_labels"] = list(labels)

        memory_scope = context.metadata.get("memory_scope")
        if isinstance(memory_scope, str) and memory_scope.strip():
            metadata["memory_scope"] = memory_scope.strip().lower()
        referral_agent_context = context.metadata.get("referral_agent_context")
        if isinstance(referral_agent_context, dict):
            metadata["referral_agent_context"] = referral_agent_context

        result = RAGOrchestrator().run(
            RAGOrchestratorInput(
                user_query=message,
                conversation_context=context,
                filters=filters,
                top_k=12,
                strict_grounding=True,
                metadata=metadata or None,
            )
        )

        return (
            result.response.answer,
            {
                "generator": "rag_orchestrator",
                "rag_used": True,
                "trace_id": result.trace_id,
                "grounding_status": result.grounding_status,
                "retrieval_summary": result.retrieval_summary,
                "warnings": list(result.warnings),
                "fallback_reason": result.fallback_reason,
                "latency_ms": result.latency_ms.get("total", 0),
            },
        )

    async def _generate_with_advanced_pipeline(
        self,
        *,
        session_id: str,
        user_id: str | None,
        message: str,
        context: ConversationContext,
    ) -> tuple[str, dict[str, Any]]:
        services = self.runtime_services
        session_context = await services.session_cache.get_session_context(session_id=session_id)

        cache_resolution = await services.cache_orchestrator.resolve_query(
            query_text=message,
            session_id=session_id,
        )
        if cache_resolution.semantic_result and cache_resolution.semantic_result.hit:
            try:
                await services.token_usage_tracker.track_cache_hit(
                    session_id=session_id,
                    endpoint="/api/v1/chat",
                    provider="openai",
                    model_name="semantic-cache",
                    metadata={
                        "cache_type": "semantic",
                        "estimated_cost_saved_usd": cache_resolution.estimated_cost_saved_usd,
                    },
                )
            except Exception:
                logger.debug("token_usage.cache_capture_failed", exc_info=True)
            cached_payload = cache_resolution.semantic_result.response.payload if cache_resolution.semantic_result.response else None
            cached_text = self._extract_message_text(cached_payload)
            if self.feature_cost_tracking_enabled and cache_resolution.estimated_cost_saved_usd is not None:
                await services.cost_tracker.record_cache_saving(
                    request_id=None,
                    provider="cache",
                    model="semantic",
                    estimated_saved_cost_usd=cache_resolution.estimated_cost_saved_usd,
                    session_id=session_id,
                    user_id=user_id,
                )
            if cached_text:
                return cached_text, {
                    "generator": "semantic_cache",
                    "rag_used": False,
                    "cache_hit": True,
                    "cache_type": "semantic",
                    "estimated_cost_saved_usd": cache_resolution.estimated_cost_saved_usd,
                }

        request_metadata: dict[str, Any] = {
            "rag_cache_hit": bool(cache_resolution.rag_result and cache_resolution.rag_result.hit),
            "retrieval_required": bool(cache_resolution.requires_retrieval),
        }
        if context.metadata.get("retrieved_docs"):
            request_metadata["retrieved_docs_present"] = True
        if isinstance(context.metadata.get("knowledge_labels"), list):
            request_metadata["knowledge_labels"] = list(context.metadata.get("knowledge_labels") or [])
        if isinstance(context.metadata.get("memory_scope"), str):
            request_metadata["memory_scope"] = str(context.metadata.get("memory_scope"))
        if isinstance(context.metadata.get("referral_agent_context"), dict):
            request_metadata["referral_agent_context"] = dict(context.metadata.get("referral_agent_context") or {})
        if isinstance(context.metadata.get("attachments"), list):
            request_metadata["attachments"] = list(context.metadata.get("attachments") or [])

        if self.feature_budget_guard_enabled:
            now = datetime.now(timezone.utc)
            daily = await services.cost_tracker.get_summary(window_start=now.replace(hour=0, minute=0, second=0, microsecond=0), window_end=now)
            monthly = await services.cost_tracker.get_summary(window_start=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), window_end=now)
            budget_decision = await services.budget_guard.evaluate_budget(daily_snapshot=daily, monthly_snapshot=monthly)
            request_metadata["budget_decision_mode"] = budget_decision.mode
            if budget_decision.mode in ("warning", "restrictive", "emergency"):
                request_metadata["budget_mode"] = "aggressive_savings"
            if budget_decision.disable_non_critical_expensive_paths:
                request_metadata["disable_expensive_paths"] = True
            if not budget_decision.allow_provider_calls:
                return (
                    "We are temporarily operating in a reduced-capacity mode. Please try again shortly.",
                    {
                        "generator": "budget_guard_degraded",
                        "rag_used": False,
                        "budget_mode": budget_decision.mode,
                    },
                )

        llm_request = LLMRequest(
            user_id=user_id,
            session_id=session_id,
            prompt=message,
            messages=[],
            metadata=request_metadata,
        )

        routing_plan = await services.model_router.build_routing_plan(llm_request)
        if self.feature_observability_adapters_enabled:
            services.llm_metrics.record_router_decision(routing_plan.primary)

        response = None
        selected_routing = routing_plan.primary
        llm_started_at = perf_counter()
        try:
            response = await services.llm_client.generate_response(llm_request, routing_plan.primary)
        except Exception as exc:
            if not self.feature_fallback_enabled:
                raise
            failover = await services.fallback_manager.evaluate_failover(
                request=llm_request,
                primary_decision=routing_plan.primary,
                failure=exc,
                attempted_routes=[routing_plan.primary],
            )
            next_route = failover.selected_route
            if next_route is None:
                raise
            if self.feature_observability_adapters_enabled:
                services.llm_metrics.record_fallback(routing_plan.primary.provider, next_route.provider)
            selected_routing = next_route
            response = await services.llm_client.generate_response(llm_request, next_route)

        if response is None:
            raise DialogueManagerError("Advanced pipeline failed to generate response.")

        if self.feature_observability_adapters_enabled:
            services.llm_metrics.record_response(response)

        if self.feature_cost_tracking_enabled:
            await services.cost_tracker.record_response(llm_request, response)

        await services.token_usage_tracker.track_llm_response(
            request=llm_request,
            response=response,
            endpoint="/api/v1/chat",
            cache_hit=False,
            started_at=llm_started_at,
            metadata={
                "routing_reason": selected_routing.reason,
                "fallback_applied": selected_routing.provider != routing_plan.primary.provider,
            },
        )

        await services.cache_orchestrator.persist_final_response(
            query_text=message,
            response_payload=response.output_text,
            metadata={
                "provider": response.provider,
                "model": response.model,
                "estimated_cost_usd": response.usage.estimated_cost_usd if response.usage else None,
            },
        )

        new_recent_messages: list[dict[str, Any]] = []
        if session_context is not None:
            new_recent_messages.extend(session_context.recent_messages[-4:])
        new_recent_messages.extend(
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": response.output_text},
            ]
        )
        await services.session_cache.update_session_context(
            session_id=session_id,
            updates={
                "user_id": user_id,
                "recent_messages": new_recent_messages[-10:],
                "dialogue_state": context.state.value,
                "user_profile_snapshot": context.user_profile.model_dump(mode="json"),
                "attributes": {"trace_source": "advanced_pipeline"},
            },
            overwrite=False,
        )

        if self.feature_shadow_routing_enabled:
            # Shadow hook: in advanced mode, we still expose routing details for benchmark diffing.
            request_metadata["shadow_route"] = {
                "provider": selected_routing.provider,
                "model": selected_routing.model,
            }

        return response.output_text, {
            "generator": "advanced_pipeline",
            "rag_used": bool(cache_resolution.rag_result and cache_resolution.rag_result.hit),
            "cache_hit": False,
            "provider": response.provider,
            "model": response.model,
            "latency_ms": response.latency_ms,
            "routing_reason": selected_routing.reason,
            "fallback_applied": selected_routing.provider != routing_plan.primary.provider,
        }

    @staticmethod
    def _extract_message_text(payload: Any) -> str | None:
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            for key in ("message", "output_text", "text", "content"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        return None

    async def _track_standard_chat_token_usage(
        self,
        *,
        session_id: str,
        user_id: str | None,
        message: str,
        assistant_message: str,
        assistant_metadata: dict[str, Any],
        trace_id: str,
        started_at: datetime,
    ) -> None:
        generator = str(assistant_metadata.get("generator", "")).strip().lower()
        if generator in {
            "advanced_pipeline",
            "simple_fallback",
            "emergency_fallback",
            "rag_orchestrator_refusal_fallback",
            "budget_guard_degraded",
            "semantic_cache",
        }:
            return

        if not bool(assistant_metadata.get("rag_used")) and not any(
            isinstance(assistant_metadata.get(key), str) and str(assistant_metadata.get(key)).strip()
            for key in ("provider", "model", "model_name", "llm_model")
        ):
            return

        if not assistant_message.strip():
            return

        provider = self._infer_provider_for_token_usage(assistant_metadata=assistant_metadata)
        model_name = self._infer_model_for_token_usage(
            assistant_metadata=assistant_metadata,
            provider=provider,
        )
        latency_ms = self._coerce_latency_ms(
            value=assistant_metadata.get("latency_ms"),
            started_at=started_at,
        )

        request = LLMRequest(
            user_id=user_id,
            session_id=session_id,
            prompt=message,
            messages=[],
            metadata={
                "trace_id": trace_id,
                "conversation_generator": generator or "unknown",
                "flow": "conversation_memory_standard",
            },
        )
        response = LLMResponse(
            request_id=request.request_id,
            provider=provider,
            model=model_name,
            output_text=assistant_message,
            usage=ProviderUsageRecord(
                provider=provider,
                model=model_name,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost_usd=0.0,
            ),
            latency_ms=latency_ms,
            raw_payload={
                "source": "conversation_memory_service",
                "generator": generator or "unknown",
            },
        )
        try:
            await self.runtime_services.token_usage_tracker.track_llm_response(
                request=request,
                response=response,
                endpoint="/api/v1/chat",
                cache_hit=False,
                metadata={
                    "generator": generator or "unknown",
                    "token_usage_mode": "metadata_only_fallback",
                },
            )
        except Exception:
            logger.debug("token_usage.standard_flow_capture_failed", exc_info=True)

    @staticmethod
    def _infer_provider_for_token_usage(*, assistant_metadata: dict[str, Any]) -> str:
        candidates = [
            assistant_metadata.get("provider"),
            assistant_metadata.get("llm_provider"),
            getattr(settings, "llm_provider", None),
        ]
        for candidate in candidates:
            if not isinstance(candidate, str) or not candidate.strip():
                continue
            normalized = candidate.strip().lower()
            if normalized == "claude":
                normalized = "anthropic"
            if normalized in {"openai", "anthropic", "deepseek"}:
                return normalized
        return "openai"

    @staticmethod
    def _infer_model_for_token_usage(*, assistant_metadata: dict[str, Any], provider: str) -> str:
        for key in ("model", "model_name", "llm_model"):
            value = assistant_metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        if provider == "anthropic":
            model = str(getattr(settings, "anthropic_generation_model", "")).strip()
            if model:
                return model
            default_model = str(getattr(settings, "default_model", "")).strip()
            return default_model or "claude-3-5-haiku-latest"

        if provider == "deepseek":
            default_model = str(getattr(settings, "default_model", "")).strip().lower()
            if default_model.startswith("deepseek"):
                return default_model
            return "deepseek-chat"

        model = str(getattr(settings, "openai_generation_model", "")).strip()
        if model:
            return model
        default_model = str(getattr(settings, "default_model", "")).strip()
        return default_model or "gpt-4o-mini"

    @staticmethod
    def _coerce_latency_ms(*, value: Any, started_at: datetime) -> int:
        if isinstance(value, (int, float)):
            return max(int(value), 0)
        elapsed = datetime.now(timezone.utc) - started_at
        return max(int(elapsed.total_seconds() * 1000), 0)

    def get_current_state(self, session_id: UUID) -> str:
        """Return normalized current state for a session."""
        state_payload = self.session_manager.get_state(session_id) or {}
        state = str(state_payload.get("state", "start"))
        return self.state_machine.normalize_state(state)

    def plan_transition(self, *, current_state: str, message: str) -> tuple[str, list[str]]:
        """Plan the next state and actions for an incoming message."""
        next_value = self.state_machine.determine_next_state(state=current_state, message=message)
        actions = self.state_machine.build_actions(old_state=current_state, new_state=next_value)
        return next_value, actions

    def build_context(self, *, session_id: UUID, state: str, message: str) -> ConversationContext:
        """Build structured conversation context for downstream consumers."""
        return self.context_manager.build_context(session_id=session_id, state=state, message=message)

    def persist_state(self, *, session_id: UUID, state: str) -> dict[str, Any] | None:
        """Persist latest state for a session."""
        return self.session_manager.update_session_state(session_id, {"state": state})

    @staticmethod
    def _resolve_user_id(session_state: SessionState, fallback_user_id: str | None) -> str | None:
        if fallback_user_id and str(fallback_user_id).strip():
            return str(fallback_user_id).strip()
        metadata_user = session_state.metadata.get("user_id")
        if metadata_user is None:
            return None
        value = str(metadata_user).strip()
        return value or None

    def _emit_outcome_event_non_blocking(
        self,
        *,
        session_id: str,
        user_id: str | None,
        persona_result: PersonaIntelligenceResponse | None,
        conversion_result: ConversionFunnelResponse | None,
    ) -> None:
        if conversion_result is None:
            return

        persona = "explorer"
        confidence = 0.0
        if persona_result is not None:
            persona = persona_result.assigned_persona.value
            confidence = max(0.0, min(1.0, persona_result.confidence_gap))

        allowed_actions = set(conversion_result.allowed_actions)
        if CTAAction.ECONOMIC in allowed_actions:
            cta_type = CTAAction.ECONOMIC
            cta_strength = EconomicSuggestionStrength.MEDIUM
        elif CTAAction.MICRO_COMMITMENT in allowed_actions:
            cta_type = CTAAction.MICRO_COMMITMENT
            cta_strength = EconomicSuggestionStrength.SOFT
        else:
            cta_type = CTAAction.EDUCATIONAL
            cta_strength = EconomicSuggestionStrength.NONE

        outcome = (
            ConversionOutcome.STAGE_ADVANCED
            if conversion_result.next_stage != conversion_result.previous_stage
            else ConversionOutcome.STAGE_HELD
        )
        cta_outcome = CTAOutcome.ALLOWED if conversion_result.blocked_reasons == [] else CTAOutcome.BLOCKED

        event = ConversionEvent(
            user_id=user_id,
            session_id=session_id,
            persona=persona,
            confidence=confidence,
            stage=conversion_result.next_stage.value,
            trust_score=conversion_result.updated_trust_score,
            engagement_score=0.0,
            triggers_used=[
                trigger
                for trigger in (conversion_result.primary_trigger, conversion_result.secondary_trigger)
                if trigger is not None
            ],
            cta_type=cta_type,
            cta_strength=cta_strength,
            outcome=outcome,
            cta_outcome=cta_outcome,
            metadata={
                "blocked_reasons": conversion_result.blocked_reasons,
                "orchestration_metadata": conversion_result.orchestration_metadata,
            },
        )

        asyncio.create_task(self.event_emitter.emit("conversion_outcome_recorded", event))
        asyncio.create_task(asyncio.to_thread(self.outcome_logger.log_conversion_outcome, event))

    @staticmethod
    def _time_of_day_bucket(hour: int) -> str:
        if hour < 5:
            return "late_night"
        if hour < 12:
            return "morning"
        if hour < 18:
            return "afternoon"
        if hour < 22:
            return "evening"
        return "night"

    def _get_or_create_session_compat(
        self,
        session_id: str | None,
        user_id: str | None,
        bootstrap_input: dict[str, Any],
    ) -> SessionState:
        try:
            return self.session_manager.get_or_create_session(
                session_id,
                user_id,
                bootstrap_input=bootstrap_input,
            )
        except TypeError:
            # Backward compatibility for legacy test doubles that still expose
            # the older (session_id, user_id) contract.
            return self.session_manager.get_or_create_session(session_id, user_id)

    @staticmethod
    def _append_turn_locally(session_state: SessionState, turn: ConversationTurn) -> SessionState:
        metadata = dict(session_state.metadata or {})
        raw_turns = metadata.get("turns", [])
        if not isinstance(raw_turns, list):
            raw_turns = []
        raw_turns.append(turn.model_dump(mode="json"))
        metadata["turns"] = raw_turns
        return session_state.model_copy(
            update={"metadata": metadata, "updated_at": datetime.now(timezone.utc)},
            deep=True,
        )

    @staticmethod
    def _build_trace_id() -> str:
        return f"cm-{int(datetime.now(timezone.utc).timestamp() * 1_000_000)}"

    def _build_ephemeral_session_state(
        self,
        *,
        user_id: str | None,
        bootstrap_input: dict[str, Any],
    ) -> SessionState:
        now = datetime.now(timezone.utc)
        ephemeral_session_id = uuid4()
        metadata: dict[str, Any] = {"turns": []}

        safe_user_id = str(user_id).strip() if user_id and str(user_id).strip() else None
        if safe_user_id:
            metadata["user_id"] = safe_user_id

        build_entry_context = getattr(self.session_manager, "_build_entry_context", None)
        if callable(build_entry_context):
            try:
                metadata["entry_context"] = build_entry_context(
                    session_id=str(ephemeral_session_id),
                    bootstrap_input=bootstrap_input,
                )
            except Exception:
                logger.warning(
                    "session.bootstrap_degraded_entry_context_failed session_id=%s",
                    ephemeral_session_id,
                )
                metadata["entry_context"] = {}
        else:
            metadata["entry_context"] = {}

        return SessionState(
            session_id=ephemeral_session_id,
            state=ConversationState.START,
            created_at=now,
            updated_at=now,
            metadata=metadata,
        )

    @staticmethod
    def _derive_memory_policy_actions(
        *,
        policy_before: SessionState,
        policy_after: SessionState,
    ) -> list[str]:
        actions: list[str] = []
        before_turns = policy_before.metadata.get("turns", [])
        after_turns = policy_after.metadata.get("turns", [])
        if isinstance(before_turns, list) and isinstance(after_turns, list):
            if len(after_turns) < len(before_turns):
                actions.append(f"trimmed_turns:{len(before_turns)}->{len(after_turns)}")
        before_summary = str(policy_before.metadata.get("memory_summary", "")).strip()
        after_summary = str(policy_after.metadata.get("memory_summary", "")).strip()
        if before_summary != after_summary:
            actions.append("updated_memory_summary")
        if not actions:
            actions.append("no_memory_policy_change")
        return actions
