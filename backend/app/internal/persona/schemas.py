"""External request/response schemas for persona analysis endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.internal.persona.enums import PersonaModifier, PersonaType


class PersonaAnalysisRequest(BaseModel):
    """Input contract for persona analysis requests."""

    session_id: str = Field(..., min_length=1, max_length=128)
    user_message: str = Field(..., min_length=1, max_length=8000)
    interaction_count: int = Field(default=1, ge=1)
    hints: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PersonaAnalysisResponse(BaseModel):
    """Output contract for persona analysis responses."""

    persona_type: PersonaType
    confidence: float = Field(..., ge=0.0, le=1.0)
    modifiers: list[PersonaModifier] = Field(default_factory=list)
    rationale: str | None = Field(default=None, min_length=1, max_length=1000)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
