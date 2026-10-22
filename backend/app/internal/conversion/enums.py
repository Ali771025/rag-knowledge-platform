"""Typed enums for conversion funnel components."""

from __future__ import annotations

from enum import Enum


class FunnelStage(str, Enum):
    """High-level conversion funnel stages."""

    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    INTENT = "intent"
    DECISION = "decision"
    CONVERSION = "conversion"


class TriggerType(str, Enum):
    """Supported trigger categories for conversion nudges and CTAs."""

    EDUCATIONAL_NUDGE = "educational_nudge"
    SOCIAL_PROOF = "social_proof"
    URGENCY_PROMPT = "urgency_prompt"
    CTA_OFFER = "cta_offer"
