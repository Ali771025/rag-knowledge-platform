from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.qora.domain.enums import ConversationStage, DepthLevel

JSONB_COMPAT = JSON().with_variant(JSONB, "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentUserState(Base):
    __tablename__ = "qora_agent_user_states"
    __table_args__ = (
        UniqueConstraint("user_id", "conversation_id", name="uq_qora_state_user_conversation"),
        Index("ix_qora_state_user_updated", "user_id", "updated_at"),
        Index("ix_qora_state_stage_updated", "conversation_stage", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    persona_core: Mapped[str | None] = mapped_column(String(32), nullable=True)
    persona_scores: Mapped[dict[str, float]] = mapped_column(JSONB_COMPAT, nullable=False, default=dict)
    persona_modifiers: Mapped[list[str]] = mapped_column(JSONB_COMPAT, nullable=False, default=list)
    depth_level: Mapped[str] = mapped_column(String(16), nullable=False, default=DepthLevel.LOW.value)
    persona_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    selected_section: Mapped[str | None] = mapped_column(String(32), nullable=True)
    current_intent: Mapped[str | None] = mapped_column(String(128), nullable=True)
    intent_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    conversation_stage: Mapped[str] = mapped_column(String(48), nullable=False, default=ConversationStage.START.value)
    matched_product: Mapped[dict[str, Any] | None] = mapped_column(JSONB_COMPAT, nullable=True)
    product_priority_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_best_action: Mapped[dict[str, Any] | None] = mapped_column(JSONB_COMPAT, nullable=True)
    current_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    readiness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reward_sensitivity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class DetectedSignal(Base):
    __tablename__ = "qora_detected_signals"
    __table_args__ = (
        Index("ix_qora_signal_conversation_detected", "conversation_id", "detected_at"),
        Index("ix_qora_signal_user_code_detected", "user_id", "signal_code", "detected_at"),
        Index("ix_qora_signal_expiry", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    turn_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("qora_conversation_turns.id"), nullable=True, index=True
    )
    signal_code: Mapped[str] = mapped_column(String(128), nullable=False)
    signal_category: Mapped[str] = mapped_column(String(64), nullable=False)
    signal_strength: Mapped[float] = mapped_column(Float, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB_COMPAT, nullable=False, default=dict)


class ConversationTurn(Base):
    __tablename__ = "qora_conversation_turns"
    __table_args__ = (
        Index("ix_qora_turn_conversation_created", "conversation_id", "created_at"),
        Index("ix_qora_turn_user_created", "user_id", "created_at"),
        Index("ix_qora_turn_request", "request_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    stage_before: Mapped[str] = mapped_column(String(48), nullable=False)
    stage_after: Mapped[str] = mapped_column(String(48), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class UserInteractionEvent(Base):
    __tablename__ = "qora_user_interaction_events"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_qora_event_event_id"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_qora_event_user_idempotency"),
        Index("ix_qora_event_conversation_occurred", "conversation_id", "occurred_at"),
        Index("ix_qora_event_user_type_occurred", "user_id", "event_type", "occurred_at"),
        Index("ix_qora_event_request", "request_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB_COMPAT, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)


class PersonaAssessment(Base):
    __tablename__ = "qora_persona_assessments"
    __table_args__ = (Index("ix_qora_assessment_conversation_created", "conversation_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    persona_scores: Mapped[dict[str, float]] = mapped_column(JSONB_COMPAT, nullable=False)
    selected_persona: Mapped[str | None] = mapped_column(String(32), nullable=True)
    modifiers: Mapped[list[str]] = mapped_column(JSONB_COMPAT, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONB_COMPAT, nullable=False, default=list)
    assessment_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class RecommendationDecision(Base):
    __tablename__ = "qora_recommendation_decisions"
    __table_args__ = (Index("ix_qora_recommendation_conversation_created", "conversation_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    selected_section: Mapped[str] = mapped_column(String(32), nullable=False)
    persona_core: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ranked_products: Mapped[list[dict[str, Any]]] = mapped_column(JSONB_COMPAT, nullable=False, default=list)
    matched_product: Mapped[dict[str, Any] | None] = mapped_column(JSONB_COMPAT, nullable=True)
    weight_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, nullable=False, default=dict)
    priority_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_best_action: Mapped[dict[str, Any] | None] = mapped_column(JSONB_COMPAT, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OrchestratorExecution(Base):
    __tablename__ = "qora_orchestrator_executions"
    __table_args__ = (
        UniqueConstraint("user_id", "conversation_id", "request_id", name="uq_qora_execution_request"),
        Index("ix_qora_execution_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="IN_PROGRESS")
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB_COMPAT, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state_version_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state_version_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class QualificationAnswer(Base):
    __tablename__ = "qora_qualification_answers"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "conversation_id", "section", "question_code",
            name="uq_qora_qualification_question",
        ),
        Index("ix_qora_qualification_conversation_section", "conversation_id", "section", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(32), nullable=False)
    question_code: Mapped[str] = mapped_column(String(64), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB_COMPAT, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ASKED")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    asked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProductWeightTableVersion(Base):
    __tablename__ = "qora_product_weight_table_versions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    weight_table_version: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class ProductCatalogItem(Base):
    __tablename__ = "qora_product_catalog_items"
    __table_args__ = (Index("ix_qora_product_section_active", "section", "is_active"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    section: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rag_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    compliance_flag: Mapped[str] = mapped_column(String(16), nullable=False, default="REVIEW")
    restrictions: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, nullable=False, default=dict)
    base_risk_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    base_friction_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB_COMPAT, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class ProductPersonaWeight(Base):
    __tablename__ = "qora_product_persona_weights"
    __table_args__ = (
        UniqueConstraint("table_version_id", "product_id", "persona_core", name="uq_qora_product_persona_weight"),
        Index("ix_qora_weight_product_persona", "product_id", "persona_core"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    table_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("qora_product_weight_table_versions.id"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        ForeignKey("qora_product_catalog_items.product_id"), nullable=False, index=True
    )
    persona_core: Mapped[str] = mapped_column(String(32), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)


class AchievementDefinition(Base):
    __tablename__ = "qora_achievement_definitions"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_qora_achievement_code_version"),
        Index("ix_qora_achievement_active_scope", "status", "section", "product_id"),
        Index("ix_qora_achievement_validity", "valid_from", "valid_to"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    section: Mapped[str | None] = mapped_column(String(32), nullable=True)
    product_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    eligible_personas: Mapped[list[str]] = mapped_column(JSONB_COMPAT, nullable=False, default=list)
    eligible_levels: Mapped[list[int]] = mapped_column(JSONB_COMPAT, nullable=False, default=list)
    required_actions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB_COMPAT, nullable=False, default=list)
    points_reward: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_token: Mapped[str | None] = mapped_column(String(32), nullable=True)
    prerequisites: Mapped[list[str]] = mapped_column(JSONB_COMPAT, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class UserAchievement(Base):
    __tablename__ = "qora_user_achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_qora_user_achievement"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_qora_user_achievement_idempotency"),
        Index("ix_qora_user_achievement_status", "user_id", "status", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    achievement_id: Mapped[UUID] = mapped_column(
        ForeignKey("qora_achievement_definitions.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    progress: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, nullable=False, default=dict)
    points_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)


class LevelDefinition(Base):
    __tablename__ = "qora_level_definitions"

    level: Mapped[int] = mapped_column(Integer, primary_key=True)
    minimum_points: Mapped[int] = mapped_column(Integer, nullable=False)
    maximum_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    unlock_rules: Mapped[dict[str, Any]] = mapped_column(JSONB_COMPAT, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)


class ReferralRuleDefinition(Base):
    __tablename__ = "qora_referral_rule_definitions"

    version: Mapped[str] = mapped_column(String(32), primary_key=True)
    reward_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    same_level_or_below_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReferralReward(Base):
    __tablename__ = "qora_referral_rewards"
    __table_args__ = (
        UniqueConstraint(
            "referrer_user_id", "referred_user_id", "source_achievement_id",
            name="uq_qora_referral_reward_source",
        ),
        UniqueConstraint("idempotency_key", name="uq_qora_referral_reward_idempotency"),
        Index("ix_qora_referral_reward_referrer_created", "referrer_user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    referrer_user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    referred_user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    source_achievement_id: Mapped[UUID] = mapped_column(
        ForeignKey("qora_achievement_definitions.id"), nullable=False
    )
    source_points: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    reward_points: Mapped[int] = mapped_column(Integer, nullable=False)
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class AchievementPointLedger(Base):
    __tablename__ = "qora_achievement_point_ledger"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_qora_point_ledger_idempotency"),
        Index("ix_qora_point_ledger_user_created", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    achievement_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("qora_achievement_definitions.id"), nullable=True
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
