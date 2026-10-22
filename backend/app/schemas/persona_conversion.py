"""External API contracts for persona and conversion orchestration endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.internal.conversion.orchestration_models import ConversionFunnelResponse
from app.internal.conversion.policy_enums import JourneyStage
from app.internal.persona.enums import PersonaType
from app.internal.persona.orchestration_models import PersonaIntelligenceResponse


class PersonaAnalyzeApiRequest(BaseModel):
    """Request model for POST /persona/analyze."""

    session_id: str = Field(..., min_length=1, max_length=128)
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=8000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    recent_messages: list[str] = Field(default_factory=list)
    current_persona: PersonaType | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PersonaAnalyzeApiResponse(PersonaIntelligenceResponse):
    """Response model for POST /persona/analyze."""


class ConversionUpdateApiRequest(BaseModel):
    """Request model for POST /conversion/update."""

    session_id: str = Field(..., min_length=1, max_length=128)
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    persona_label: str = Field(..., min_length=1, max_length=64)
    persona_confidence: float = Field(..., ge=0.0, le=1.0)
    trust_score: float = Field(..., ge=0.0, le=1.0)
    current_stage: JourneyStage = JourneyStage.ENTRY
    intent: str = Field(default="", max_length=256)
    is_ambiguous: bool = False
    repeated_interaction_count: int = Field(default=0, ge=0)
    clarification_success_count: int = Field(default=0, ge=0)
    objection_count: int = Field(default=0, ge=0)
    confusion_count: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConversionUpdateApiResponse(ConversionFunnelResponse):
    """Response model for POST /conversion/update."""
