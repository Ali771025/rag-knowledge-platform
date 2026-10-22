from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.qora.domain.enums import (
    ConversationStage,
    DepthLevel,
    PersonaCore,
    PersonaModifier,
    Section,
    SignalSourceType,
)


class SignalCandidate(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    category: str = Field(min_length=1, max_length=64)
    strength: float = Field(ge=0.0, le=1.0)
    source: SignalSourceType
    evidence: str | None = Field(default=None, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SignalParserResult(BaseModel):
    signals: list[SignalCandidate] = Field(default_factory=list)
    intent_candidates: list[str] = Field(default_factory=list)
    ambiguity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    used_llm: bool = False
    fallback_used: bool = False
    errors: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class PersonaDecision(BaseModel):
    persona_core: PersonaCore | None
    scores: dict[PersonaCore, float]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    needs_reassessment: bool = False
    discovery_oriented: bool = False
    candidate_personas: list[PersonaCore] = Field(default_factory=list, max_length=2)

    model_config = ConfigDict(extra="forbid")

    @field_validator("scores")
    @classmethod
    def validate_scores(cls, value: dict[PersonaCore, float]) -> dict[PersonaCore, float]:
        if set(value) != set(PersonaCore):
            raise ValueError("scores must contain every PersonaCore")
        if any(score < 0.0 or score > 1.0 for score in value.values()):
            raise ValueError("persona scores must be between 0 and 1")
        return value


class ModifierDecision(BaseModel):
    name: PersonaModifier
    score: float = Field(ge=0.0, le=1.0)
    active: bool
    evidence: list[str] = Field(default_factory=list)
    response_effect: str


class DepthPolicy(BaseModel):
    level: DepthLevel
    answer_length: str
    technical_vocabulary: str
    number_of_reasons: int = Field(ge=1)
    number_of_sources: int = Field(ge=0)
    number_of_options: int = Field(ge=1, le=2)
    cta_intensity: str
    detail_level: str
    risk_disclosure_depth: str
    architecture_detail: str
    cautious_tone: bool = False


class AgentStateSnapshot(BaseModel):
    id: UUID
    user_id: UUID
    conversation_id: UUID
    persona_core: PersonaCore | None
    persona_scores: dict[str, float]
    persona_modifiers: list[PersonaModifier]
    depth_level: DepthLevel
    persona_confidence: float
    selected_section: Section | None
    current_intent: str | None
    intent_confidence: float
    conversation_stage: ConversationStage
    matched_product: dict[str, Any] | None
    product_priority_reason: str | None
    next_best_action: dict[str, Any] | None
    current_points: int
    current_level: int
    readiness_score: float
    reward_sensitivity: float
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

