"""add QORA achievement protocol and auditable point ledger

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-22 00:00:00.000000
"""

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    json_type = postgresql.JSONB(astext_type=sa.Text()) if op.get_bind().dialect.name == "postgresql" else sa.JSON()
    op.create_table(
        "qora_achievement_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("section", sa.String(length=32), nullable=True),
        sa.Column("product_id", sa.String(length=64), nullable=True),
        sa.Column("eligible_personas", json_type, nullable=False),
        sa.Column("eligible_levels", json_type, nullable=False),
        sa.Column("required_actions", json_type, nullable=False),
        sa.Column("points_reward", sa.Integer(), nullable=False),
        sa.Column("reward_token", sa.String(length=32), nullable=True),
        sa.Column("prerequisites", json_type, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("points_reward >= 0", name="ck_qora_achievement_points_nonnegative"),
        sa.CheckConstraint("status IN ('DRAFT','ACTIVE','RETIRED')", name="ck_qora_achievement_definition_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "version", name="uq_qora_achievement_code_version"),
    )
    op.create_index("ix_qora_achievement_definitions_code", "qora_achievement_definitions", ["code"])
    op.create_index("ix_qora_achievement_definitions_status", "qora_achievement_definitions", ["status"])
    op.create_index("ix_qora_achievement_active_scope", "qora_achievement_definitions", ["status", "section", "product_id"])
    op.create_index("ix_qora_achievement_validity", "qora_achievement_definitions", ["valid_from", "valid_to"])

    op.create_table(
        "qora_level_definitions",
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("minimum_points", sa.Integer(), nullable=False),
        sa.Column("maximum_points", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("unlock_rules", json_type, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.CheckConstraint("minimum_points >= 0", name="ck_qora_level_minimum_nonnegative"),
        sa.CheckConstraint("maximum_points IS NULL OR maximum_points >= minimum_points", name="ck_qora_level_range"),
        sa.CheckConstraint("status IN ('DRAFT','ACTIVE','RETIRED')", name="ck_qora_level_status"),
        sa.PrimaryKeyConstraint("level"),
    )
    op.create_index("ix_qora_level_definitions_status", "qora_level_definitions", ["status"])

    op.create_table(
        "qora_referral_rule_definitions",
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("reward_percentage", sa.Float(), nullable=False),
        sa.Column("same_level_or_below_only", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("reward_percentage >= 0 AND reward_percentage <= 1", name="ck_qora_referral_percentage"),
        sa.CheckConstraint("status IN ('DRAFT','ACTIVE','RETIRED')", name="ck_qora_referral_rule_status"),
        sa.PrimaryKeyConstraint("version"),
    )
    op.create_index("ix_qora_referral_rule_definitions_status", "qora_referral_rule_definitions", ["status"])

    op.create_table(
        "qora_user_achievements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("achievement_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("progress", json_type, nullable=False),
        sa.Column("points_awarded", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.CheckConstraint("status IN ('AVAILABLE','STARTED','COMPLETED','EXPIRED')", name="ck_qora_user_achievement_status"),
        sa.CheckConstraint("points_awarded >= 0", name="ck_qora_user_achievement_points"),
        sa.ForeignKeyConstraint(["achievement_id"], ["qora_achievement_definitions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "achievement_id", name="uq_qora_user_achievement"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_qora_user_achievement_idempotency"),
    )
    op.create_index("ix_qora_user_achievements_user_id", "qora_user_achievements", ["user_id"])
    op.create_index("ix_qora_user_achievements_achievement_id", "qora_user_achievements", ["achievement_id"])
    op.create_index("ix_qora_user_achievement_status", "qora_user_achievements", ["user_id", "status", "started_at"])

    op.create_table(
        "qora_referral_rewards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("referrer_user_id", sa.Uuid(), nullable=False),
        sa.Column("referred_user_id", sa.Uuid(), nullable=False),
        sa.Column("source_achievement_id", sa.Uuid(), nullable=False),
        sa.Column("source_points", sa.Integer(), nullable=False),
        sa.Column("reward_percentage", sa.Float(), nullable=False),
        sa.Column("reward_points", sa.Integer(), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(length=128), nullable=False),
        sa.Column("rule_version", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source_points >= 0 AND reward_points >= 0", name="ck_qora_referral_points"),
        sa.ForeignKeyConstraint(["source_achievement_id"], ["qora_achievement_definitions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("referrer_user_id", "referred_user_id", "source_achievement_id", name="uq_qora_referral_reward_source"),
        sa.UniqueConstraint("idempotency_key", name="uq_qora_referral_reward_idempotency"),
    )
    op.create_index("ix_qora_referral_rewards_referrer_user_id", "qora_referral_rewards", ["referrer_user_id"])
    op.create_index("ix_qora_referral_rewards_referred_user_id", "qora_referral_rewards", ["referred_user_id"])
    op.create_index("ix_qora_referral_reward_referrer_created", "qora_referral_rewards", ["referrer_user_id", "created_at"])

    op.create_table(
        "qora_achievement_point_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("achievement_id", sa.Uuid(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("rule_version", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("points >= 0", name="ck_qora_point_ledger_points"),
        sa.CheckConstraint("source_type IN ('PERSONAL_ACHIEVEMENT','REFERRAL')", name="ck_qora_point_ledger_source"),
        sa.ForeignKeyConstraint(["achievement_id"], ["qora_achievement_definitions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_qora_point_ledger_idempotency"),
    )
    op.create_index("ix_qora_achievement_point_ledger_user_id", "qora_achievement_point_ledger", ["user_id"])
    op.create_index("ix_qora_point_ledger_user_created", "qora_achievement_point_ledger", ["user_id", "created_at"])

    now = datetime(2026, 7, 22, tzinfo=timezone.utc)
    level_table = sa.table(
        "qora_level_definitions",
        sa.column("level", sa.Integer()), sa.column("minimum_points", sa.Integer()),
        sa.column("maximum_points", sa.Integer()), sa.column("title", sa.String()),
        sa.column("unlock_rules", json_type), sa.column("status", sa.String()),
    )
    # Interim cumulative interpretation follows the supplied 82/250 Level Card example.
    op.bulk_insert(level_table, [
        {"level": 1, "minimum_points": 0, "maximum_points": 249, "title": "Level 1", "unlock_rules": {"document_threshold": 100, "threshold_semantics": "INTERIM_MILESTONE"}, "status": "ACTIVE"},
        {"level": 2, "minimum_points": 250, "maximum_points": None, "title": "Level 2", "unlock_rules": {"document_threshold": 250, "threshold_semantics": "CUMULATIVE"}, "status": "ACTIVE"},
    ])
    rule_table = sa.table(
        "qora_referral_rule_definitions",
        sa.column("version", sa.String()), sa.column("reward_percentage", sa.Float()),
        sa.column("same_level_or_below_only", sa.Boolean()), sa.column("status", sa.String()),
        sa.column("effective_from", sa.DateTime(timezone=True)), sa.column("effective_to", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(rule_table, [{
        "version": "qora-referral-v1", "reward_percentage": 0.10,
        "same_level_or_below_only": True, "status": "ACTIVE",
        "effective_from": now, "effective_to": None,
    }])


def downgrade() -> None:
    op.drop_table("qora_achievement_point_ledger")
    op.drop_table("qora_referral_rewards")
    op.drop_table("qora_user_achievements")
    op.drop_table("qora_referral_rule_definitions")
    op.drop_table("qora_level_definitions")
    op.drop_table("qora_achievement_definitions")
