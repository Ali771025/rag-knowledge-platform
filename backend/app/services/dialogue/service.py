"""Minimal dialogue integration hooks for persona and conversion modules."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from typing import Any, Protocol

from app.internal.conversion import (
    ConversionFunnelRequest,
    ConversionFunnelService,
    JourneyStage,
)
from app.internal.persona import (
    PersonaIntelligenceRequest,
    PersonaIntelligenceService,
    PersonaType,
)
from app.internal.persona.transition_buffer_repository import RedisPersonaTransitionBufferRepository
from app.internal.persona.transition_manager import PersonaTransitionManager
from app.internal.conversion.enums import FunnelStage
from app.internal.policy.loader import load_default_policy_config

logger = logging.getLogger(__name__)


class PersonaHook(Protocol):
    """Callback interface for persona hooks attached to dialogue processing."""

    def on_message(self, *, session_id: str, message: str, state: str) -> dict[str, Any] | None:
        """Receive user message metadata for persona-related side effects."""


class ConversionHook(Protocol):
    """Callback interface for conversion hooks attached to dialogue processing."""

    def on_message(self, *, session_id: str, message: str, state: str) -> dict[str, Any] | None:
        """Receive user message metadata for conversion-related side effects."""


@dataclass(frozen=True, slots=True)
class DialogueIntelligenceHooks:
    """Container that wires optional persona/conversion hooks into dialogue manager."""

    persona_hook: PersonaHook | None = None
    conversion_hook: ConversionHook | None = None


@dataclass(frozen=True, slots=True)
class DialoguePolicySnapshot:
    """Minimal policy snapshot exported for dialogue-aware modules."""

    persona_confidence_threshold: float
    cta_min_stage: FunnelStage
    default_persona: PersonaType


class LoggingEventEmitter:
    """Simple logger-backed event emitter for domain orchestration events."""

    def emit(self, event_name: str, payload: dict) -> None:  # noqa: ANN401
        logger.info("dialogue_orchestration_event event=%s payload=%s", event_name, payload)


class PersonaServiceHook:
    """Dialogue hook adapter that invokes persona orchestration service safely."""

    def __init__(self, service: PersonaIntelligenceService) -> None:
        self.service = service

    def on_message(self, *, session_id: str, message: str, state: str) -> dict[str, Any] | None:
        _ = state
        result = _run_sync(
            self.service.analyze(
                PersonaIntelligenceRequest(
                    session_id=session_id,
                    message=message,
                    metadata={},
                    recent_messages=[],
                )
            )
        )
        if result is None:
            return None
        return result.model_dump(mode="json")


class ConversionServiceHook:
    """Dialogue hook adapter that invokes conversion funnel service safely."""

    def __init__(self, service: ConversionFunnelService) -> None:
        self.service = service

    def on_message(self, *, session_id: str, message: str, state: str) -> dict[str, Any] | None:
        stage = _map_dialogue_state_to_journey_stage(state)
        result = _run_sync(
            self.service.update(
                ConversionFunnelRequest(
                    session_id=session_id,
                    persona_label="explorer",
                    persona_confidence=0.0,
                    trust_score=0.25,
                    current_stage=stage,
                    intent=message,
                )
            )
        )
        if result is None:
            return None
        return result.model_dump(mode="json")


@dataclass(frozen=True, slots=True)
class DialogueOrchestrationServices:
    """Persona and conversion services wired for dialogue orchestration flows."""

    persona_service: PersonaIntelligenceService
    conversion_service: ConversionFunnelService


def load_dialogue_policy_snapshot() -> DialoguePolicySnapshot:
    """Load a read-only policy snapshot for consumers that only need defaults."""

    config = load_default_policy_config()
    return DialoguePolicySnapshot(
        persona_confidence_threshold=config.persona.confidence_threshold,
        cta_min_stage=config.conversion.cta_policy.min_stage_for_cta,
        default_persona=PersonaType.EXPLORER,
    )


def build_dialogue_orchestration_services() -> DialogueOrchestrationServices:
    """Build default persona/conversion orchestration services for dialogue flows."""

    config = load_default_policy_config()
    emitter = LoggingEventEmitter()

    transition_manager = PersonaTransitionManager(
        buffer_store=RedisPersonaTransitionBufferRepository(ttl_seconds=1800, max_items=3),
        min_score_multiplier=config.persona.transition.min_score_multiplier,
        stability_window=config.persona.transition.stability_window,
        trust_low_speed_penalty=config.persona.transition.trust_low_speed_penalty,
    )
    persona_service = PersonaIntelligenceService(
        transition_manager=transition_manager,
        policy_config=config,
        event_emitter=emitter,
    )
    conversion_service = ConversionFunnelService(
        policy_config=config,
        event_emitter=emitter,
    )
    return DialogueOrchestrationServices(
        persona_service=persona_service,
        conversion_service=conversion_service,
    )


def _run_sync(coro):  # noqa: ANN001, ANN201
    try:
        asyncio.get_running_loop()
        return None
    except RuntimeError:
        try:
            return asyncio.run(coro)
        except Exception:
            logger.warning("dialogue hook orchestration failed", exc_info=True)
            return None


def _map_dialogue_state_to_journey_stage(state: str) -> JourneyStage:
    value = state.strip().lower()
    mapping = {
        "start": JourneyStage.ENTRY,
        "intro": JourneyStage.EXPLORATION,
        "education": JourneyStage.TRUST_FORMATION,
        "qna": JourneyStage.OPPORTUNITY_AWARENESS,
        "join": JourneyStage.MICRO_COMMITMENT,
    }
    return mapping.get(value, JourneyStage.ENTRY)
