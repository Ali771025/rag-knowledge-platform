from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from urllib.parse import urlparse

from app.qora.domain.enums import ConversationStage, DepthLevel, PersonaCore, PersonaModifier, Section
from app.qora.domain.achievement import AchievementContext, LevelCard


class InteractionEventInput(BaseModel):
    event_type: str = Field(min_length=1, max_length=64)
    entity_type: str | None = Field(default=None, max_length=64)
    entity_id: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=128)


class PageContext(BaseModel):
    page: str | None = None
    explicit_section: Section | None = None
    explicit_product_id: str | None = None
    language: str = "fa"
    metadata: dict[str, Any] = Field(default_factory=dict)


class UIOption(BaseModel):
    id: str
    label: str
    value: str


class UIBlock(BaseModel):
    type: str
    options: list[UIOption] = Field(default_factory=list)
    cards: list[dict[str, Any]] = Field(default_factory=list)
    level_card: LevelCard | None = None
    achievement_card: AchievementContext | None = None


class CTA(BaseModel):
    type: str
    label: str
    target: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class Progress(BaseModel):
    current_step: int = Field(ge=1)
    total_steps: int = Field(ge=1)


class SourceReference(BaseModel):
    source_id: str
    chunk_id: str | None = None
    title: str | None = None
    source_type: str | None = None
    content_version: str | None = None
    url: str | None = None
    claim_ids: list[str] = Field(default_factory=list)

    @field_validator("url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source URL must use http or https")
        return value


class NextBestAction(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class OrchestratorResponse(BaseModel):
    request_id: str
    conversation_id: str
    stage: ConversationStage
    message: str
    response_type: str = "GUIDANCE"
    title: str | None = None
    ui: UIBlock
    primary_cta: CTA | None = None
    secondary_cta: CTA | None = None
    progress: Progress
    sources: list[SourceReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_best_action: NextBestAction | None = None
    can_continue: bool = True

    model_config = ConfigDict(extra="forbid")


class IntentDecision(BaseModel):
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)


class SectionDecision(BaseModel):
    selected_section: Section | None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    requires_qualification: bool = True


class QualificationQuestion(BaseModel):
    code: str
    text: str
    options: list[UIOption]
    uncertainty_dimension: str


class QualificationStatus(BaseModel):
    complete: bool
    completeness: float = Field(ge=0.0, le=1.0)
    answered: dict[str, dict[str, Any]] = Field(default_factory=dict)
    next_questions: list[QualificationQuestion] = Field(default_factory=list, max_length=4)


class ProductScoreComponents(BaseModel):
    persona_weight: float
    intent_match: float
    qualification_match: float
    eligibility: float
    readiness_score: float
    behavior_match: float
    risk_penalty: float
    friction_penalty: float
    final_score: float


class RankedProduct(BaseModel):
    product_id: str
    section: Section
    eligible: bool
    scores: ProductScoreComponents
    reason_codes: list[str]
    exclusion_reasons: list[str] = Field(default_factory=list)


class RankingDecision(BaseModel):
    weight_table_version: str
    ranked_products: list[RankedProduct]
    matched_product: RankedProduct | None
    confidence: float
    priority_reason: str | None


class CompositionContext(BaseModel):
    persona_core: PersonaCore | None
    modifiers: list[PersonaModifier]
    depth_level: DepthLevel
    intent: str
    selected_section: Section | None
    matched_product: str | None
    priority_reason: str | None = None
    conversation_stage: ConversationStage
    rag_sources: list[SourceReference]
    rag_excerpt: str | None = None
    insufficient_context: bool = False
    allowed_claims: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    next_best_action: NextBestAction | None = None
    qualification_question: QualificationQuestion | None = None
    readiness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    achievement_context: AchievementContext | None = None
    level_card: LevelCard | None = None


class GuardrailResult(BaseModel):
    valid: bool
    reason_codes: list[str] = Field(default_factory=list)
    severity: Literal["NONE", "WARN", "BLOCK"] = "NONE"
