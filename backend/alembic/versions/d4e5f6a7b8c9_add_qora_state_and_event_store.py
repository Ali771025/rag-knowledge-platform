"""add QORA state and append-only event store

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-17 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERSONAS = "'SAVER','HUNTER','PLAYER','ARCHITECT'"
DEPTHS = "'LOW','MEDIUM','HIGH'"
SECTIONS = "'INVESTMENT','EARN','STOCKHOLDERS','DEVELOPMENT','EDUCATION'"
STAGES = (
    "'START','GREETING','WHAT_IS_THIS','SIGNAL_CAPTURE','PERSONA_CLASSIFICATION',"
    "'MODIFIER_CLASSIFICATION','DEPTH_SELECTION','SECTION_DISCOVERY','NEED_QUALIFICATION',"
    "'WEIGHT_MATCHING','PRODUCT_PRIORITIZATION','PRODUCT_INTRODUCTION','ACHIEVEMENT_OVERLAY',"
    "'CTA','NEXT_BEST_ACTION','FEEDBACK_OBSERVATION','PERSONA_REASSESSMENT'"
)


def upgrade() -> None:
    json_type = postgresql.JSONB(astext_type=sa.Text()) if op.get_bind().dialect.name == "postgresql" else sa.JSON()
    op.create_table(
        "qora_agent_user_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("persona_core", sa.String(length=32), nullable=True),
        sa.Column("persona_scores", json_type, nullable=False),
        sa.Column("persona_modifiers", json_type, nullable=False),
        sa.Column("depth_level", sa.String(length=16), nullable=False),
        sa.Column("persona_confidence", sa.Float(), nullable=False),
        sa.Column("selected_section", sa.String(length=32), nullable=True),
        sa.Column("current_intent", sa.String(length=128), nullable=True),
        sa.Column("intent_confidence", sa.Float(), nullable=False),
        sa.Column("conversation_stage", sa.String(length=48), nullable=False),
        sa.Column("matched_product", json_type, nullable=True),
        sa.Column("product_priority_reason", sa.Text(), nullable=True),
        sa.Column("next_best_action", json_type, nullable=True),
        sa.Column("current_points", sa.Integer(), nullable=False),
        sa.Column("current_level", sa.Integer(), nullable=False),
        sa.Column("readiness_score", sa.Float(), nullable=False),
        sa.Column("reward_sensitivity", sa.Float(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(f"persona_core IS NULL OR persona_core IN ({PERSONAS})", name="ck_qora_state_persona"),
        sa.CheckConstraint(f"depth_level IN ({DEPTHS})", name="ck_qora_state_depth"),
        sa.CheckConstraint(f"selected_section IS NULL OR selected_section IN ({SECTIONS})", name="ck_qora_state_section"),
        sa.CheckConstraint(f"conversation_stage IN ({STAGES})", name="ck_qora_state_stage"),
        sa.CheckConstraint("version >= 1", name="ck_qora_state_version"),
        sa.CheckConstraint("persona_confidence BETWEEN 0 AND 1", name="ck_qora_state_persona_confidence"),
        sa.CheckConstraint("intent_confidence BETWEEN 0 AND 1", name="ck_qora_state_intent_confidence"),
        sa.CheckConstraint("readiness_score BETWEEN 0 AND 1", name="ck_qora_state_readiness"),
        sa.CheckConstraint("reward_sensitivity BETWEEN 0 AND 1", name="ck_qora_state_reward_sensitivity"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "conversation_id", name="uq_qora_state_user_conversation"),
    )
    op.create_index("ix_qora_agent_user_states_user_id", "qora_agent_user_states", ["user_id"])
    op.create_index("ix_qora_agent_user_states_conversation_id", "qora_agent_user_states", ["conversation_id"])
    op.create_index("ix_qora_state_user_updated", "qora_agent_user_states", ["user_id", "updated_at"])
    op.create_index("ix_qora_state_stage_updated", "qora_agent_user_states", ["conversation_stage", "updated_at"])

    op.create_table(
        "qora_conversation_turns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("normalized_message", sa.Text(), nullable=True),
        sa.Column("stage_before", sa.String(length=48), nullable=False),
        sa.Column("stage_after", sa.String(length=48), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('USER','ASSISTANT','SYSTEM')", name="ck_qora_turn_role"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qora_conversation_turns_conversation_id", "qora_conversation_turns", ["conversation_id"])
    op.create_index("ix_qora_conversation_turns_user_id", "qora_conversation_turns", ["user_id"])
    op.create_index("ix_qora_turn_conversation_created", "qora_conversation_turns", ["conversation_id", "created_at"])
    op.create_index("ix_qora_turn_user_created", "qora_conversation_turns", ["user_id", "created_at"])
    op.create_index("ix_qora_turn_request", "qora_conversation_turns", ["request_id"])

    op.create_table(
        "qora_detected_signals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("turn_id", sa.Uuid(), nullable=True),
        sa.Column("signal_code", sa.String(length=128), nullable=False),
        sa.Column("signal_category", sa.String(length=64), nullable=False),
        sa.Column("signal_strength", sa.Float(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_value", sa.Text(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", json_type, nullable=False),
        sa.CheckConstraint("signal_strength BETWEEN 0 AND 1", name="ck_qora_signal_strength"),
        sa.ForeignKeyConstraint(["turn_id"], ["qora_conversation_turns.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qora_detected_signals_user_id", "qora_detected_signals", ["user_id"])
    op.create_index("ix_qora_detected_signals_conversation_id", "qora_detected_signals", ["conversation_id"])
    op.create_index("ix_qora_detected_signals_turn_id", "qora_detected_signals", ["turn_id"])
    op.create_index("ix_qora_signal_conversation_detected", "qora_detected_signals", ["conversation_id", "detected_at"])
    op.create_index("ix_qora_signal_user_code_detected", "qora_detected_signals", ["user_id", "signal_code", "detected_at"])
    op.create_index("ix_qora_signal_expiry", "qora_detected_signals", ["expires_at"])

    op.create_table(
        "qora_user_interaction_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", json_type, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_qora_event_event_id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_qora_event_user_idempotency"),
    )
    op.create_index("ix_qora_user_interaction_events_user_id", "qora_user_interaction_events", ["user_id"])
    op.create_index("ix_qora_user_interaction_events_conversation_id", "qora_user_interaction_events", ["conversation_id"])
    op.create_index("ix_qora_event_conversation_occurred", "qora_user_interaction_events", ["conversation_id", "occurred_at"])
    op.create_index("ix_qora_event_user_type_occurred", "qora_user_interaction_events", ["user_id", "event_type", "occurred_at"])
    op.create_index("ix_qora_event_request", "qora_user_interaction_events", ["request_id"])

    op.create_table(
        "qora_persona_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("persona_scores", json_type, nullable=False),
        sa.Column("selected_persona", sa.String(length=32), nullable=True),
        sa.Column("modifiers", json_type, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence", json_type, nullable=False),
        sa.Column("assessment_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(f"selected_persona IS NULL OR selected_persona IN ({PERSONAS})", name="ck_qora_assessment_persona"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_qora_assessment_confidence"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qora_persona_assessments_user_id", "qora_persona_assessments", ["user_id"])
    op.create_index("ix_qora_persona_assessments_conversation_id", "qora_persona_assessments", ["conversation_id"])
    op.create_index("ix_qora_assessment_conversation_created", "qora_persona_assessments", ["conversation_id", "created_at"])

    op.create_table(
        "qora_recommendation_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("selected_section", sa.String(length=32), nullable=False),
        sa.Column("persona_core", sa.String(length=32), nullable=True),
        sa.Column("ranked_products", json_type, nullable=False),
        sa.Column("matched_product", json_type, nullable=True),
        sa.Column("weight_snapshot", json_type, nullable=False),
        sa.Column("priority_reason", sa.Text(), nullable=True),
        sa.Column("next_best_action", json_type, nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(f"selected_section IN ({SECTIONS})", name="ck_qora_recommendation_section"),
        sa.CheckConstraint(f"persona_core IS NULL OR persona_core IN ({PERSONAS})", name="ck_qora_recommendation_persona"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_qora_recommendation_confidence"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qora_recommendation_decisions_user_id", "qora_recommendation_decisions", ["user_id"])
    op.create_index("ix_qora_recommendation_decisions_conversation_id", "qora_recommendation_decisions", ["conversation_id"])
    op.create_index("ix_qora_recommendation_conversation_created", "qora_recommendation_decisions", ["conversation_id", "created_at"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE FUNCTION qora_reject_event_mutation() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'qora_user_interaction_events is append-only';
            END;
            $$ LANGUAGE plpgsql;
            CREATE TRIGGER trg_qora_events_append_only
            BEFORE UPDATE OR DELETE ON qora_user_interaction_events
            FOR EACH ROW EXECUTE FUNCTION qora_reject_event_mutation();
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_qora_events_append_only ON qora_user_interaction_events")
        op.execute("DROP FUNCTION IF EXISTS qora_reject_event_mutation()")
    op.drop_table("qora_recommendation_decisions")
    op.drop_table("qora_persona_assessments")
    op.drop_table("qora_user_interaction_events")
    op.drop_table("qora_detected_signals")
    op.drop_table("qora_conversation_turns")
    op.drop_table("qora_agent_user_states")
