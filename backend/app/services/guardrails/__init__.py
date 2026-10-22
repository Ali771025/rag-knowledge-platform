"""Guardrails package initialization and shared exports."""

from app.services.guardrails.constants import (
    ALLOWED_ETER_DOMAIN_KEYWORDS,
    ALLOWED_ETER_FEATURE_KEYWORDS,
    BLOCKED_PHASE1_ACTIONS,
    BLOCKED_TOPICS,
    COMPETITOR_KEYWORDS,
    FABRICATION_UNCERTAINTY_PHRASES,
    FALLBACK_MESSAGES,
    FORBIDDEN_PHASE1_REQUEST_PATTERNS,
    FORBIDDEN_OUTPUT_ACTION_PHRASES,
    GENERIC_BLOCKCHAIN_KEYWORDS,
    PROMPT_INJECTION_PATTERNS,
    UNSAFE_ACTION_PHRASES,
    UNSAFE_OUTPUT_PATTERNS,
)
from app.services.guardrails.dialogue_adapter import GuardrailsDialogueAdapter
from app.services.guardrails.domain_guard import detect_off_topic, is_query_allowed
from app.services.guardrails.models import (
    Document,
    FallbackAction,
    GroundingResult,
    InjectionResult,
    OffTopicResult,
    OutputValidationResult,
    PreSafetyResult,
    ResponseStrategy,
    RiskLevel,
    SafetyFlag,
    SafetyOrchestratorResult,
    ValidationResult,
)
from app.services.guardrails.prompt_injection_detector import detect_prompt_injection
from app.services.guardrails.retrieval_validator import validate_retrieval
from app.services.guardrails.confidence_engine import (
    apply_uncertainty_disclaimer,
    calculate_confidence,
    determine_response_strategy,
)
from app.services.guardrails.grounding_verifier import verify_grounding
from app.services.guardrails.output_filter import validate_output
from app.services.guardrails.safety_logging import SafetyLogger
from app.services.guardrails.safety_metrics import SafetyMetrics
from app.services.guardrails.safety_orchestrator import (
    SafetyOrchestrator,
    post_check_generated_response,
    pre_check_user_query,
    process_safe_response,
)

__all__ = [
    "ALLOWED_ETER_DOMAIN_KEYWORDS",
    "ALLOWED_ETER_FEATURE_KEYWORDS",
    "BLOCKED_PHASE1_ACTIONS",
    "BLOCKED_TOPICS",
    "COMPETITOR_KEYWORDS",
    "calculate_confidence",
    "determine_response_strategy",
    "detect_off_topic",
    "detect_prompt_injection",
    "Document",
    "FABRICATION_UNCERTAINTY_PHRASES",
    "FALLBACK_MESSAGES",
    "FallbackAction",
    "FORBIDDEN_PHASE1_REQUEST_PATTERNS",
    "FORBIDDEN_OUTPUT_ACTION_PHRASES",
    "GENERIC_BLOCKCHAIN_KEYWORDS",
    "GuardrailsDialogueAdapter",
    "GroundingResult",
    "InjectionResult",
    "is_query_allowed",
    "OffTopicResult",
    "OutputValidationResult",
    "post_check_generated_response",
    "PreSafetyResult",
    "pre_check_user_query",
    "PROMPT_INJECTION_PATTERNS",
    "apply_uncertainty_disclaimer",
    "ResponseStrategy",
    "RiskLevel",
    "SafetyFlag",
    "SafetyOrchestrator",
    "SafetyLogger",
    "SafetyMetrics",
    "SafetyOrchestratorResult",
    "UNSAFE_ACTION_PHRASES",
    "UNSAFE_OUTPUT_PATTERNS",
    "ValidationResult",
    "process_safe_response",
    "validate_output",
    "validate_retrieval",
    "verify_grounding",
]
