"""Persona intelligence contracts and domain models."""

from app.internal.persona.config import PersonaEngineConfig
from app.internal.persona.confidence_engine import (
    NEUTRAL_ASSIGNMENT,
    PersonaConfidenceResult,
    evaluate_persona_confidence,
)
from app.internal.persona.enums import PersonaModifier, PersonaType
from app.internal.persona.events import PersonaAnalyzedEvent, PersonaEventEnvelope, PersonaModifierAppliedEvent
from app.internal.persona.models import PersonaAnalysisResult
from app.internal.persona.modifier_detector import ModifierDetectionResult, ModifierEvaluation, detect_persona_modifiers
from app.internal.persona.persona_scorer import (
    PersonaScoreBreakdown,
    PersonaScoringResult,
    SignalContribution,
    score_persona_signals,
)
from app.internal.persona.orchestration_models import (
    PersonaIntelligenceRequest,
    PersonaIntelligenceResponse,
    PersonaTransitionSummary,
)
from app.internal.persona.schemas import PersonaAnalysisRequest, PersonaAnalysisResponse
from app.internal.persona.service import (
    NoopPersonaEventEmitter,
    PersonaEventEmitter,
    PersonaIntelligenceService,
)
from app.internal.persona.signal_extractor import extract_persona_signals
from app.internal.persona.signal_models import ExtractedPersonaSignals, PersonaSignal
from app.internal.persona.transition_buffer_models import (
    PersonaTransitionBuffer,
    PersonaTransitionEvaluation,
    TransitionCandidate,
)
from app.internal.persona.transition_buffer_repository import (
    PersonaTransitionBufferStore,
    RedisPersonaTransitionBufferRepository,
)
from app.internal.persona.transition_manager import (
    PersonaTransitionDecision,
    PersonaTransitionHistoryWriter,
    PersonaTransitionManager,
    TransitionReason,
)

__all__ = [
    "PersonaAnalysisRequest",
    "PersonaAnalysisResponse",
    "PersonaAnalysisResult",
    "PersonaAnalyzedEvent",
    "PersonaEventEnvelope",
    "PersonaModifier",
    "PersonaModifierAppliedEvent",
    "PersonaType",
    "PersonaEngineConfig",
    "NEUTRAL_ASSIGNMENT",
    "PersonaConfidenceResult",
    "evaluate_persona_confidence",
    "ModifierDetectionResult",
    "ModifierEvaluation",
    "detect_persona_modifiers",
    "PersonaIntelligenceRequest",
    "PersonaIntelligenceResponse",
    "PersonaTransitionSummary",
    "PersonaEventEmitter",
    "NoopPersonaEventEmitter",
    "PersonaIntelligenceService",
    "PersonaScoreBreakdown",
    "PersonaScoringResult",
    "SignalContribution",
    "score_persona_signals",
    "extract_persona_signals",
    "ExtractedPersonaSignals",
    "PersonaSignal",
    "PersonaTransitionBuffer",
    "PersonaTransitionBufferStore",
    "PersonaTransitionEvaluation",
    "RedisPersonaTransitionBufferRepository",
    "TransitionCandidate",
    "PersonaTransitionDecision",
    "PersonaTransitionHistoryWriter",
    "PersonaTransitionManager",
    "TransitionReason",
]
