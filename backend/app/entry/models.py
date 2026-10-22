"""Shared entry-context contracts for early-session intent/risk hints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.internal.conversion.policy_enums import EntryProbableIntent, EntryRiskProfileHint
from app.internal.persona.enums import PersonaModifier


class EntryContextInput(BaseModel):
    """Typed input contract for session entry-context analysis."""

    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(default="", max_length=4000)
    referrer_id: str | None = Field(default=None, min_length=1, max_length=128)
    referral_link_type: str | None = Field(default=None, min_length=1, max_length=64)
    network_position: str | None = Field(default=None, min_length=1, max_length=64)
    device_info: dict[str, Any] = Field(default_factory=dict)
    language_hint: str | None = Field(default=None, min_length=1, max_length=32)
    time_of_day: str | None = Field(default=None, min_length=1, max_length=32)
    campaign_source: str | None = Field(default=None, min_length=1, max_length=128)
    medium: str | None = Field(default=None, min_length=1, max_length=64)
    pre_engagement: str | None = Field(default=None, min_length=1, max_length=128)
    trust_score: float | None = Field(default=None, ge=0.0, le=1.0)
    modifiers: list[PersonaModifier] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EntryContextOutput(BaseModel):
    """Typed output contract with probable intent/risk hints."""

    referrer_type: str = Field(default="unknown", min_length=1, max_length=64)
    campaign_type: str = Field(default="unknown", min_length=1, max_length=64)
    probable_intent: EntryProbableIntent = EntryProbableIntent.UNKNOWN
    risk_profile_hint: EntryRiskProfileHint = EntryRiskProfileHint.UNKNOWN
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str = Field(..., min_length=1, max_length=512)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
