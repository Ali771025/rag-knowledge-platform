"""Conversion funnel contracts and domain models."""

from app.internal.conversion.config import ConversionEngineConfig
from app.internal.conversion.conversion_rules import (
    ConversionDecisionAction,
    ConversionDecisionPolicyConfig,
    ConversionDecisionRule,
    ConversionDecisionRuleCondition,
    ConversionDecisionThresholds,
    ConversionRulesError,
    load_conversion_decision_policy,
    load_default_conversion_decision_policy,
)
from app.internal.conversion.conversion_policy import (
    ConversionPolicyConfig,
    ConversionPolicyInput,
    ConversionPolicyResult,
    evaluate_conversion_policy,
)
from app.internal.conversion.cta_gatekeeper import CTAGatekeeper, CTAGatekeeperDecision
from app.internal.conversion.enums import FunnelStage, TriggerType
from app.internal.conversion.events import (
    ConversionDecisionEvaluatedEvent,
    ConversionEventEnvelope,
    ConversionEvaluatedEvent,
    TriggerSelectedEvent,
)
from app.internal.conversion.funnel_fsm import (
    FunnelFSMConfig,
    FunnelStageFSM,
    FunnelTransitionInput,
    FunnelTransitionResult,
    GuardCheck,
)
from app.internal.conversion.models import ConversionEvaluationResult
from app.internal.conversion.orchestration_models import ConversionFunnelRequest, ConversionFunnelResponse
from app.internal.conversion.rule_engine import (
    ConversionDecisionAllowedAction,
    ConversionDecisionRuleEngine,
    ConversionDecisionRuleInput,
    ConversionDecisionRuleOutput,
)
from app.internal.conversion.policy_enums import (
    CTAAction,
    CTAOutcome,
    ConversionActionType,
    ConversionOutcome,
    EconomicSuggestionStrength,
    EntryProbableIntent,
    EntryRiskProfileHint,
    JourneyStage,
    PsychologicalTrigger,
    TriggerType as PolicyTriggerType,
)
from app.internal.conversion.schemas import ConversionEvaluationRequest, ConversionEvaluationResponse
from app.internal.conversion.service import (
    ConversionEventEmitter,
    ConversionFunnelService,
    NoopConversionEventEmitter,
)
from app.internal.conversion.trigger_selector import (
    TriggerSelectionConfig,
    TriggerSelectionEngine,
    TriggerSelectionInput,
    TriggerSelectionResult,
)
from app.internal.conversion.trust_engine import TrustScoreReason, TrustScoreResult, update_trust_score

__all__ = [
    "ConversionEngineConfig",
    "ConversionPolicyConfig",
    "ConversionPolicyInput",
    "ConversionPolicyResult",
    "evaluate_conversion_policy",
    "ConversionDecisionAction",
    "ConversionDecisionPolicyConfig",
    "ConversionDecisionRule",
    "ConversionDecisionRuleCondition",
    "ConversionDecisionThresholds",
    "ConversionRulesError",
    "load_conversion_decision_policy",
    "load_default_conversion_decision_policy",
    "CTAGatekeeper",
    "CTAGatekeeperDecision",
    "ConversionEvaluationRequest",
    "ConversionEvaluationResponse",
    "ConversionEvaluationResult",
    "ConversionFunnelRequest",
    "ConversionFunnelResponse",
    "ConversionEventEmitter",
    "NoopConversionEventEmitter",
    "ConversionFunnelService",
    "ConversionEventEnvelope",
    "ConversionDecisionEvaluatedEvent",
    "ConversionEvaluatedEvent",
    "FunnelFSMConfig",
    "FunnelStageFSM",
    "FunnelTransitionInput",
    "FunnelTransitionResult",
    "GuardCheck",
    "CTAAction",
    "CTAOutcome",
    "ConversionActionType",
    "ConversionOutcome",
    "EconomicSuggestionStrength",
    "EntryProbableIntent",
    "EntryRiskProfileHint",
    "JourneyStage",
    "PolicyTriggerType",
    "PsychologicalTrigger",
    "TriggerSelectionConfig",
    "TriggerSelectionEngine",
    "TriggerSelectionInput",
    "TriggerSelectionResult",
    "FunnelStage",
    "TriggerSelectedEvent",
    "TriggerType",
    "TrustScoreReason",
    "TrustScoreResult",
    "update_trust_score",
    "ConversionDecisionAllowedAction",
    "ConversionDecisionRuleEngine",
    "ConversionDecisionRuleInput",
    "ConversionDecisionRuleOutput",
]
