"""Enums used by funnel FSM, trigger selection, and conversion policy engines."""

from __future__ import annotations

from enum import Enum


class JourneyStage(str, Enum):
    """Deterministic funnel journey stages."""

    ENTRY = "entry"
    EXPLORATION = "exploration"
    TRUST_FORMATION = "trust_formation"
    OPPORTUNITY_AWARENESS = "opportunity_awareness"
    MICRO_COMMITMENT = "micro_commitment"
    ECONOMIC_ACTION = "economic_action"


class PsychologicalTrigger(str, Enum):
    """Policy-supported persuasion/engagement trigger categories."""

    CURIOSITY = "curiosity"
    LOSS_AVOIDANCE = "loss_avoidance"
    SOCIAL_PROOF = "social_proof"
    SCARCITY = "scarcity"
    CONTROL = "control"
    TRANSPARENCY = "transparency"
    OPPORTUNITY_FRAMING = "opportunity_framing"
    MICRO_COMMITMENT = "micro_commitment"
    FUTURE_SELF = "future_self"
    AUTHORITY = "authority"


class CTAAction(str, Enum):
    """Supported CTA actions emitted by conversion policy engine."""

    EDUCATIONAL = "educational"
    MICRO_COMMITMENT = "micro_commitment"
    ECONOMIC = "economic"


# Shared contract aliases / enums for Part 2 compatibility.
TriggerType = PsychologicalTrigger
ConversionActionType = CTAAction


class EconomicSuggestionStrength(str, Enum):
    """Strength level for economic CTA/suggestion framing."""

    NONE = "none"
    SOFT = "soft"
    MEDIUM = "medium"
    MODERATE = "medium"
    STRONG = "strong"


class CTAOutcome(str, Enum):
    """Outcome of CTA gatekeeping decision."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    DEFERRED = "deferred"


class ConversionOutcome(str, Enum):
    """Outcome of conversion decision step."""

    NO_CHANGE = "no_change"
    STAGE_ADVANCED = "stage_advanced"
    STAGE_HELD = "stage_held"
    ECONOMIC_ACTION_READY = "economic_action_ready"


class EntryProbableIntent(str, Enum):
    """Probable intent hint inferred during entry/session bootstrap."""

    EXPLORER = "explorer"
    SKEPTIC = "skeptic"
    INVESTOR = "investor"
    UNKNOWN = "unknown"


class EntryRiskProfileHint(str, Enum):
    """Risk profile hint inferred during entry/session bootstrap."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"
