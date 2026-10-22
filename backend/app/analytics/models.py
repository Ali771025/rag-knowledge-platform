"""Shared analytics contracts for trigger and conversion decision telemetry."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.internal.conversion.policy_enums import ConversionOutcome, TriggerType


class TriggerAnalyticsRecord(BaseModel):
    """Analytics record for trigger selection decisions."""

    session_id: str = Field(..., min_length=1, max_length=128)
    primary_trigger: TriggerType
    secondary_trigger: TriggerType | None = None
    intensity: float = Field(..., ge=0.0, le=1.0)
    stage: str = Field(..., min_length=1, max_length=64)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConversionAnalyticsRecord(BaseModel):
    """Analytics record for conversion decision outcomes."""

    session_id: str = Field(..., min_length=1, max_length=128)
    persona: str = Field(..., min_length=1, max_length=64)
    outcome: ConversionOutcome
    trust_score: float = Field(..., ge=0.0, le=1.0)
    stage: str = Field(..., min_length=1, max_length=64)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
