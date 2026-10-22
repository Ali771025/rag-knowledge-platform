"""add persona and conversion persistence tables

Revision ID: f4a1c2d3e4b5
Revises: c3d8f84f2a11
Create Date: 2026-05-15 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f4a1c2d3e4b5"
down_revision: Union[str, None] = "c3d8f84f2a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


persona_type_enum = sa.Enum("explorer", "analyst", "pragmatist", "executor", name="persona_type_enum")
persona_modifier_enum = sa.Enum(
    "high_intent",
    "budget_sensitive",
    "risk_averse",
    "time_constrained",
    name="persona_modifier_enum",
)
funnel_stage_enum = sa.Enum(
    "awareness",
    "consideration",
    "intent",
    "decision",
    "conversion",
    name="funnel_stage_enum",
)
trigger_type_enum = sa.Enum(
    "educational_nudge",
    "social_proof",
    "urgency_prompt",
    "cta_offer",
    name="trigger_type_enum",
)
persona_type_enum_column = postgresql.ENUM(
    "explorer",
    "analyst",
    "pragmatist",
    "executor",
    name="persona_type_enum",
    create_type=False,
)
persona_modifier_enum_column = postgresql.ENUM(
    "high_intent",
    "budget_sensitive",
    "risk_averse",
    "time_constrained",
    name="persona_modifier_enum",
    create_type=False,
)
funnel_stage_enum_column = postgresql.ENUM(
    "awareness",
    "consideration",
    "intent",
    "decision",
    "conversion",
    name="funnel_stage_enum",
    create_type=False,
)
trigger_type_enum_column = postgresql.ENUM(
    "educational_nudge",
    "social_proof",
    "urgency_prompt",
    "cta_offer",
    name="trigger_type_enum",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN CREATE TYPE persona_type_enum AS ENUM ('explorer', 'analyst', 'pragmatist', 'executor'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE persona_modifier_enum AS ENUM "
        "('high_intent', 'budget_sensitive', 'risk_averse', 'time_constrained'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE funnel_stage_enum AS ENUM "
        "('awareness', 'consideration', 'intent', 'decision', 'conversion'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE trigger_type_enum AS ENUM "
        "('educational_nudge', 'social_proof', 'urgency_prompt', 'cta_offer'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )

    op.create_table(
        "persona_state",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("persona_type", persona_type_enum_column, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("active_modifiers", sa.JSON(), nullable=False),
        sa.Column("signals_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_persona_state_session_id"),
    )
    op.create_index(op.f("ix_persona_state_session_id"), "persona_state", ["session_id"], unique=False)
    op.create_index(op.f("ix_persona_state_user_id"), "persona_state", ["user_id"], unique=False)
    op.create_index(
        "ix_persona_state_session_updated",
        "persona_state",
        ["session_id", "updated_at"],
        unique=False,
    )

    op.create_table(
        "persona_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("persona_state_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("previous_persona_type", persona_type_enum_column, nullable=True),
        sa.Column("new_persona_type", persona_type_enum_column, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_persona_history_persona_state_id"), "persona_history", ["persona_state_id"], unique=False)
    op.create_index(op.f("ix_persona_history_session_id"), "persona_history", ["session_id"], unique=False)
    op.create_index(op.f("ix_persona_history_created_at"), "persona_history", ["created_at"], unique=False)
    op.create_index(
        "ix_persona_history_session_created",
        "persona_history",
        ["session_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "modifier_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("persona_state_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("modifier", persona_modifier_enum_column, nullable=False),
        sa.Column("is_applied", sa.Boolean(), nullable=False),
        sa.Column("trigger_type", trigger_type_enum_column, nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_modifier_history_persona_state_id"), "modifier_history", ["persona_state_id"], unique=False)
    op.create_index(op.f("ix_modifier_history_session_id"), "modifier_history", ["session_id"], unique=False)
    op.create_index(op.f("ix_modifier_history_created_at"), "modifier_history", ["created_at"], unique=False)
    op.create_index(
        "ix_modifier_history_session_created",
        "modifier_history",
        ["session_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "funnel_state",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("stage", funnel_stage_enum_column, nullable=False),
        sa.Column("stage_confidence", sa.Float(), nullable=False),
        sa.Column("cta_allowed", sa.Boolean(), nullable=False),
        sa.Column("state_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_funnel_state_session_id"),
    )
    op.create_index(op.f("ix_funnel_state_session_id"), "funnel_state", ["session_id"], unique=False)
    op.create_index(op.f("ix_funnel_state_user_id"), "funnel_state", ["user_id"], unique=False)
    op.create_index(
        "ix_funnel_state_session_updated",
        "funnel_state",
        ["session_id", "updated_at"],
        unique=False,
    )

    op.create_table(
        "conversion_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("funnel_state_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", trigger_type_enum_column, nullable=False),
        sa.Column("stage", funnel_stage_enum_column, nullable=False),
        sa.Column("persona_type", persona_type_enum_column, nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversion_events_session_id"), "conversion_events", ["session_id"], unique=False)
    op.create_index(op.f("ix_conversion_events_funnel_state_id"), "conversion_events", ["funnel_state_id"], unique=False)
    op.create_index(op.f("ix_conversion_events_created_at"), "conversion_events", ["created_at"], unique=False)
    op.create_index(
        "ix_conversion_events_session_created",
        "conversion_events",
        ["session_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversion_events_session_created", table_name="conversion_events")
    op.drop_index(op.f("ix_conversion_events_created_at"), table_name="conversion_events")
    op.drop_index(op.f("ix_conversion_events_funnel_state_id"), table_name="conversion_events")
    op.drop_index(op.f("ix_conversion_events_session_id"), table_name="conversion_events")
    op.drop_table("conversion_events")

    op.drop_index("ix_funnel_state_session_updated", table_name="funnel_state")
    op.drop_index(op.f("ix_funnel_state_user_id"), table_name="funnel_state")
    op.drop_index(op.f("ix_funnel_state_session_id"), table_name="funnel_state")
    op.drop_table("funnel_state")

    op.drop_index("ix_modifier_history_session_created", table_name="modifier_history")
    op.drop_index(op.f("ix_modifier_history_created_at"), table_name="modifier_history")
    op.drop_index(op.f("ix_modifier_history_session_id"), table_name="modifier_history")
    op.drop_index(op.f("ix_modifier_history_persona_state_id"), table_name="modifier_history")
    op.drop_table("modifier_history")

    op.drop_index("ix_persona_history_session_created", table_name="persona_history")
    op.drop_index(op.f("ix_persona_history_created_at"), table_name="persona_history")
    op.drop_index(op.f("ix_persona_history_session_id"), table_name="persona_history")
    op.drop_index(op.f("ix_persona_history_persona_state_id"), table_name="persona_history")
    op.drop_table("persona_history")

    op.drop_index("ix_persona_state_session_updated", table_name="persona_state")
    op.drop_index(op.f("ix_persona_state_user_id"), table_name="persona_state")
    op.drop_index(op.f("ix_persona_state_session_id"), table_name="persona_state")
    op.drop_table("persona_state")

    bind = op.get_bind()
    trigger_type_enum.drop(bind, checkfirst=True)
    funnel_stage_enum.drop(bind, checkfirst=True)
    persona_modifier_enum.drop(bind, checkfirst=True)
    persona_type_enum.drop(bind, checkfirst=True)
