"""add analytics outcome persistence tables and conversion event fields

Revision ID: 8b9d3f7a1c2e
Revises: f4a1c2d3e4b5
Create Date: 2026-05-18 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "8b9d3f7a1c2e"
down_revision: Union[str, None] = "f4a1c2d3e4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB()
    return sa.JSON()


def _json_list_default() -> sa.TextClause:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.text("'[]'::jsonb")
    return sa.text("'[]'")


def _json_dict_default() -> sa.TextClause:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.text("'{}'::jsonb")
    return sa.text("'{}'")


def upgrade() -> None:
    op.add_column("conversion_events", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.add_column(
        "conversion_events",
        sa.Column("persona", sa.String(length=64), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "conversion_events",
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "conversion_events",
        sa.Column("trust_score", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "conversion_events",
        sa.Column("engagement_score", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "conversion_events",
        sa.Column("triggers_used", _json_type(), nullable=False, server_default=_json_list_default()),
    )
    op.add_column("conversion_events", sa.Column("cta_type", sa.String(length=64), nullable=True))
    op.add_column(
        "conversion_events",
        sa.Column("cta_strength", sa.String(length=32), nullable=False, server_default="none"),
    )
    op.add_column(
        "conversion_events",
        sa.Column("outcome", sa.String(length=64), nullable=False, server_default="no_change"),
    )
    op.add_column("conversion_events", sa.Column("cta_outcome", sa.String(length=32), nullable=True))
    op.add_column("conversion_events", sa.Column("experiment_name", sa.String(length=64), nullable=True))
    op.add_column("conversion_events", sa.Column("experiment_variant", sa.String(length=64), nullable=True))

    op.alter_column(
        "conversion_events",
        "metadata_json",
        existing_type=sa.JSON(),
        type_=_json_type(),
        existing_nullable=False,
        server_default=_json_dict_default(),
    )

    op.create_index("ix_conversion_events_user_id", "conversion_events", ["user_id"], unique=False)
    op.create_index("ix_conversion_events_persona", "conversion_events", ["persona"], unique=False)
    op.create_index("ix_conversion_events_stage", "conversion_events", ["stage"], unique=False)
    op.create_index("ix_conversion_events_outcome", "conversion_events", ["outcome"], unique=False)

    op.create_table(
        "trigger_effectiveness",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trigger_primary", sa.String(length=64), nullable=False),
        sa.Column("trigger_secondary", sa.String(length=64), nullable=True),
        sa.Column("persona", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("success_rate", sa.Float(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_trigger_effectiveness_trigger_primary",
        "trigger_effectiveness",
        ["trigger_primary"],
        unique=False,
    )
    op.create_index(
        "ix_trigger_effectiveness_persona",
        "trigger_effectiveness",
        ["persona"],
        unique=False,
    )
    op.create_index(
        "ix_trigger_effectiveness_stage",
        "trigger_effectiveness",
        ["stage"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_trigger_effectiveness_stage", table_name="trigger_effectiveness")
    op.drop_index("ix_trigger_effectiveness_persona", table_name="trigger_effectiveness")
    op.drop_index("ix_trigger_effectiveness_trigger_primary", table_name="trigger_effectiveness")
    op.drop_table("trigger_effectiveness")

    op.drop_index("ix_conversion_events_outcome", table_name="conversion_events")
    op.drop_index("ix_conversion_events_stage", table_name="conversion_events")
    op.drop_index("ix_conversion_events_persona", table_name="conversion_events")
    op.drop_index("ix_conversion_events_user_id", table_name="conversion_events")

    op.drop_column("conversion_events", "experiment_variant")
    op.drop_column("conversion_events", "experiment_name")
    op.drop_column("conversion_events", "cta_outcome")
    op.drop_column("conversion_events", "outcome")
    op.drop_column("conversion_events", "cta_strength")
    op.drop_column("conversion_events", "cta_type")
    op.drop_column("conversion_events", "triggers_used")
    op.drop_column("conversion_events", "engagement_score")
    op.drop_column("conversion_events", "trust_score")
    op.drop_column("conversion_events", "confidence")
    op.drop_column("conversion_events", "persona")
    op.drop_column("conversion_events", "user_id")
