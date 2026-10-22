"""External request/response schemas for conversion evaluation endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.internal.conversion.enums import FunnelStage, TriggerType
from app.internal.persona.enums import PersonaType


class ConversionEvaluationRequest(BaseModel):
    """Input contract for conversion evaluation requests."""

    session_id: str = Field(..., min_length=1, max_length=128)
    persona_type: PersonaType
    current_stage: FunnelStage
    latest_message: str = Field(..., min_length=1, max_length=8000)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConversionEvaluationResponse(BaseModel):
    """Output contract for conversion evaluation requests."""

    next_stage: FunnelStage
    trigger_type: TriggerType | None = None
    cta_allowed: bool = False
    confidence: float = Field(..., ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")
