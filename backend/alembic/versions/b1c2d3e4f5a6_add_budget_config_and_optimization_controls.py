"""add budget config and optimization controls

Revision ID: b1c2d3e4f5a6
Revises: a9b8c7d6e5f4
Create Date: 2026-05-31 00:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_key_budget_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("api_key_id", sa.Uuid(), nullable=False),
        sa.Column("monthly_budget_usd", sa.Numeric(precision=18, scale=9), nullable=True),
        sa.Column("alert_thresholds_json", sa.JSON(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("api_key_id", name="uq_api_key_budget_configs_api_key_id"),
    )
    op.create_index("ix_api_key_budget_configs_api_key_id", "api_key_budget_configs", ["api_key_id"], unique=False)

    op.create_table(
        "budget_change_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("api_key_id", sa.Uuid(), nullable=False),
        sa.Column("changed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("old_monthly_budget_usd", sa.Numeric(precision=18, scale=9), nullable=True),
        sa.Column("new_monthly_budget_usd", sa.Numeric(precision=18, scale=9), nullable=True),
        sa.Column("old_alert_thresholds_json", sa.JSON(), nullable=False),
        sa.Column("new_alert_thresholds_json", sa.JSON(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_budget_change_audit_logs_api_key_id", "budget_change_audit_logs", ["api_key_id"], unique=False)
    op.create_index(
        "ix_budget_change_audit_logs_changed_by_user_id",
        "budget_change_audit_logs",
        ["changed_by_user_id"],
        unique=False,
    )
    op.create_index("ix_budget_change_audit_logs_changed_at", "budget_change_audit_logs", ["changed_at"], unique=False)

    op.add_column("budget_alerts", sa.Column("threshold_percent", sa.Integer(), nullable=True))
    op.add_column("budget_alerts", sa.Column("budget_usd", sa.Numeric(precision=18, scale=9), nullable=True))
    op.add_column("budget_alerts", sa.Column("cycle_start", sa.Date(), nullable=True))
    op.add_column("budget_alerts", sa.Column("cycle_end", sa.Date(), nullable=True))
    op.add_column("budget_alerts", sa.Column("status", sa.String(length=16), nullable=False, server_default="active"))
    op.create_index("ix_budget_alerts_cycle_start", "budget_alerts", ["cycle_start"], unique=False)
    op.create_index("ix_budget_alerts_status", "budget_alerts", ["status"], unique=False)
    op.create_unique_constraint(
        "uq_budget_alerts_api_key_cycle_threshold",
        "budget_alerts",
        ["api_key_id", "cycle_start", "threshold_percent"],
    )

    op.add_column("optimization_recommendations", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "optimization_recommendations",
        sa.Column("potential_saving_usd", sa.Numeric(precision=18, scale=9), nullable=False, server_default="0"),
    )
    op.add_column(
        "optimization_recommendations",
        sa.Column("action_items_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column("optimization_recommendations", sa.Column("dedupe_key", sa.String(length=128), nullable=True))
    op.create_index(
        "ix_optimization_recommendations_dedupe_key",
        "optimization_recommendations",
        ["dedupe_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_optimization_recommendations_dedupe_key", table_name="optimization_recommendations")
    op.drop_column("optimization_recommendations", "dedupe_key")
    op.drop_column("optimization_recommendations", "action_items_json")
    op.drop_column("optimization_recommendations", "potential_saving_usd")
    op.drop_column("optimization_recommendations", "description")

    op.drop_constraint("uq_budget_alerts_api_key_cycle_threshold", "budget_alerts", type_="unique")
    op.drop_index("ix_budget_alerts_status", table_name="budget_alerts")
    op.drop_index("ix_budget_alerts_cycle_start", table_name="budget_alerts")
    op.drop_column("budget_alerts", "status")
    op.drop_column("budget_alerts", "cycle_end")
    op.drop_column("budget_alerts", "cycle_start")
    op.drop_column("budget_alerts", "budget_usd")
    op.drop_column("budget_alerts", "threshold_percent")

    op.drop_index("ix_budget_change_audit_logs_changed_at", table_name="budget_change_audit_logs")
    op.drop_index("ix_budget_change_audit_logs_changed_by_user_id", table_name="budget_change_audit_logs")
    op.drop_index("ix_budget_change_audit_logs_api_key_id", table_name="budget_change_audit_logs")
    op.drop_table("budget_change_audit_logs")

    op.drop_index("ix_api_key_budget_configs_api_key_id", table_name="api_key_budget_configs")
    op.drop_table("api_key_budget_configs")
