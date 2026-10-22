"""add user profile and onboarding milestone tables

Revision ID: e7a1b9c2d3f4
Revises: b1c2d3e4f5a6
Create Date: 2026-06-04 21:25:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e7a1b9c2d3f4"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


knowledge_level_enum = sa.Enum("beginner", "intermediate", "advanced", name="knowledge_level")
personality_type_enum = sa.Enum("analytical", "practical", "creative", "social", name="personality_type")
response_style_enum = sa.Enum("concise", "detailed", "balanced", name="response_style")


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'knowledge_level') THEN
                    CREATE TYPE knowledge_level AS ENUM ('beginner', 'intermediate', 'advanced');
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'personality_type') THEN
                    CREATE TYPE personality_type AS ENUM ('analytical', 'practical', 'creative', 'social');
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'response_style') THEN
                    CREATE TYPE response_style AS ENUM ('concise', 'detailed', 'balanced');
                END IF;
            END
            $$;
            """
        )
        knowledge_level_column_type = postgresql.ENUM(
            "beginner", "intermediate", "advanced", name="knowledge_level", create_type=False
        )
        personality_type_column_type = postgresql.ENUM(
            "analytical", "practical", "creative", "social", name="personality_type", create_type=False
        )
        response_style_column_type = postgresql.ENUM(
            "concise", "detailed", "balanced", name="response_style", create_type=False
        )
    else:
        knowledge_level_enum.create(bind, checkfirst=True)
        personality_type_enum.create(bind, checkfirst=True)
        response_style_enum.create(bind, checkfirst=True)
        knowledge_level_column_type = knowledge_level_enum
        personality_type_column_type = personality_type_enum
        response_style_column_type = response_style_enum

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_level", knowledge_level_column_type, nullable=False),
        sa.Column("personality_type", personality_type_column_type, nullable=True),
        sa.Column("preferred_response_style", response_style_column_type, nullable=False),
        sa.Column("onboarding_progress", sa.Float(), nullable=False),
        sa.Column("last_state", sa.String(length=100), nullable=False),
        sa.Column("completed_milestones", sa.JSON(), nullable=False),
        sa.Column("engagement_score", sa.Float(), nullable=False),
        sa.Column("total_messages", sa.Integer(), nullable=False),
        sa.Column("total_sessions", sa.Integer(), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_profiles_user_id"), "user_profiles", ["user_id"], unique=True)

    op.create_table(
        "onboarding_milestones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("milestone_name", sa.String(length=255), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_onboarding_milestones_user_id"), "onboarding_milestones", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    op.drop_index(op.f("ix_onboarding_milestones_user_id"), table_name="onboarding_milestones")
    op.drop_table("onboarding_milestones")
    op.drop_index(op.f("ix_user_profiles_user_id"), table_name="user_profiles")
    op.drop_table("user_profiles")

    if dialect_name == "postgresql":
        op.execute("DROP TYPE IF EXISTS response_style")
        op.execute("DROP TYPE IF EXISTS personality_type")
        op.execute("DROP TYPE IF EXISTS knowledge_level")
    else:
        response_style_enum.drop(bind, checkfirst=True)
        personality_type_enum.drop(bind, checkfirst=True)
        knowledge_level_enum.drop(bind, checkfirst=True)
