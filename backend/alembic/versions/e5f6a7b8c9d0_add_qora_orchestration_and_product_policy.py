"""add QORA orchestration, qualification, and product policy

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-17 00:30:00.000000
"""

from datetime import datetime, timezone
from typing import Sequence, Union
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

WEIGHTS: dict[str, dict[str, int]] = {
    "ETER": {"SAVER": 1, "HUNTER": 1, "ARCHITECT": 1, "PLAYER": 4},
    "Q": {"SAVER": 4, "HUNTER": 3, "ARCHITECT": 5, "PLAYER": 1},
    "STAKING": {"SAVER": 3, "HUNTER": 2, "ARCHITECT": 4, "PLAYER": 5},
    "EID": {"SAVER": 5, "HUNTER": 5, "ARCHITECT": 3, "PLAYER": 3},
    "INSURANCE": {"SAVER": 2, "HUNTER": 4, "ARCHITECT": 2, "PLAYER": 2},
    "EES": {"SAVER": 1, "HUNTER": 1, "ARCHITECT": 2, "PLAYER": 1},
    "ERA": {"SAVER": 2, "HUNTER": 2, "ARCHITECT": 1, "PLAYER": 2},
    "PROPOSAL": {"SAVER": 2, "HUNTER": 2, "ARCHITECT": 1, "PLAYER": 2},
    "ELITE": {"SAVER": 1, "HUNTER": 1, "ARCHITECT": 2, "PLAYER": 1},
    "FAN_COMMUNITY": {"SAVER": 2, "HUNTER": 2, "ARCHITECT": 2, "PLAYER": 2},
    "REFERRAL_INSURANCE": {"SAVER": 1, "HUNTER": 3, "ARCHITECT": 3, "PLAYER": 3},
    "FORECAST": {"SAVER": 3, "HUNTER": 1, "ARCHITECT": 1, "PLAYER": 1},
    "EDGE": {"SAVER": 1, "HUNTER": 1, "ARCHITECT": 1, "PLAYER": 1},
}

SECTIONS = {
    "ETER": "INVESTMENT", "Q": "INVESTMENT", "STAKING": "INVESTMENT", "EID": "INVESTMENT", "INSURANCE": "INVESTMENT",
    "EES": "STOCKHOLDERS", "ERA": "STOCKHOLDERS",
    "PROPOSAL": "DEVELOPMENT", "ELITE": "DEVELOPMENT",
    "FAN_COMMUNITY": "EARN", "REFERRAL_INSURANCE": "EARN", "FORECAST": "EARN",
    "EDGE": "EDUCATION",
}


def upgrade() -> None:
    json_type = postgresql.JSONB(astext_type=sa.Text()) if op.get_bind().dialect.name == "postgresql" else sa.JSON()
    op.create_table(
        "qora_orchestrator_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("response_payload", json_type, nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("state_version_before", sa.Integer(), nullable=True),
        sa.Column("state_version_after", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('IN_PROGRESS','COMPLETED','FAILED')", name="ck_qora_execution_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "conversation_id", "request_id", name="uq_qora_execution_request"),
    )
    op.create_index("ix_qora_orchestrator_executions_user_id", "qora_orchestrator_executions", ["user_id"])
    op.create_index("ix_qora_orchestrator_executions_conversation_id", "qora_orchestrator_executions", ["conversation_id"])
    op.create_index("ix_qora_execution_conversation_created", "qora_orchestrator_executions", ["conversation_id", "created_at"])

    op.create_table(
        "qora_qualification_answers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("section", sa.String(length=32), nullable=False),
        sa.Column("question_code", sa.String(length=64), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("answer_value", json_type, nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("asked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('ASKED','ANSWERED')", name="ck_qora_qualification_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "conversation_id", "section", "question_code", name="uq_qora_qualification_question"),
    )
    op.create_index("ix_qora_qualification_answers_user_id", "qora_qualification_answers", ["user_id"])
    op.create_index("ix_qora_qualification_answers_conversation_id", "qora_qualification_answers", ["conversation_id"])
    op.create_index("ix_qora_qualification_conversation_section", "qora_qualification_answers", ["conversation_id", "section", "status"])

    op.create_table(
        "qora_product_weight_table_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("weight_table_version", sa.String(length=64), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("approved_by", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('DRAFT','APPROVED','ACTIVE','RETIRED')", name="ck_qora_weight_version_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("weight_table_version"),
    )
    op.create_index("ix_qora_product_weight_table_versions_weight_table_version", "qora_product_weight_table_versions", ["weight_table_version"])
    op.create_index("ix_qora_product_weight_table_versions_effective_from", "qora_product_weight_table_versions", ["effective_from"])
    op.create_index("ix_qora_product_weight_table_versions_status", "qora_product_weight_table_versions", ["status"])

    op.create_table(
        "qora_product_catalog_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.String(length=64), nullable=False),
        sa.Column("section", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("rag_ready", sa.Boolean(), nullable=False),
        sa.Column("compliance_flag", sa.String(length=16), nullable=False),
        sa.Column("restrictions", json_type, nullable=False),
        sa.Column("base_risk_penalty", sa.Float(), nullable=False),
        sa.Column("base_friction_penalty", sa.Float(), nullable=False),
        sa.Column("metadata", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("compliance_flag IN ('CLEAR','REVIEW','BLOCKED')", name="ck_qora_product_compliance"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id"),
    )
    op.create_index("ix_qora_product_catalog_items_product_id", "qora_product_catalog_items", ["product_id"])
    op.create_index("ix_qora_product_section_active", "qora_product_catalog_items", ["section", "is_active"])

    op.create_table(
        "qora_product_persona_weights",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("table_version_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.String(length=64), nullable=False),
        sa.Column("persona_core", sa.String(length=32), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.CheckConstraint("persona_core IN ('SAVER','HUNTER','PLAYER','ARCHITECT')", name="ck_qora_weight_persona"),
        sa.CheckConstraint("weight >= 0", name="ck_qora_weight_nonnegative"),
        sa.ForeignKeyConstraint(["product_id"], ["qora_product_catalog_items.product_id"]),
        sa.ForeignKeyConstraint(["table_version_id"], ["qora_product_weight_table_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("table_version_id", "product_id", "persona_core", name="uq_qora_product_persona_weight"),
    )
    op.create_index("ix_qora_product_persona_weights_table_version_id", "qora_product_persona_weights", ["table_version_id"])
    op.create_index("ix_qora_product_persona_weights_product_id", "qora_product_persona_weights", ["product_id"])
    op.create_index("ix_qora_weight_product_persona", "qora_product_persona_weights", ["product_id", "persona_core"])

    now = datetime(2026, 7, 17, tzinfo=timezone.utc)
    version_id = uuid5(NAMESPACE_URL, "qora-weight-v1")
    version_table = sa.table(
        "qora_product_weight_table_versions",
        sa.column("id", sa.Uuid()), sa.column("weight_table_version", sa.String()),
        sa.column("effective_from", sa.DateTime(timezone=True)), sa.column("effective_to", sa.DateTime(timezone=True)),
        sa.column("created_by", sa.String()), sa.column("approved_by", sa.String()), sa.column("status", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(version_table, [{
        "id": version_id, "weight_table_version": "qora-product-weights-v1", "effective_from": now,
        "effective_to": None, "created_by": "phase-four-spec", "approved_by": "phase-four-spec",
        "status": "ACTIVE", "created_at": now,
    }])
    catalog_table = sa.table(
        "qora_product_catalog_items",
        sa.column("id", sa.Uuid()), sa.column("product_id", sa.String()), sa.column("section", sa.String()),
        sa.column("display_name", sa.String()), sa.column("is_active", sa.Boolean()), sa.column("rag_ready", sa.Boolean()),
        sa.column("compliance_flag", sa.String()), sa.column("restrictions", json_type),
        sa.column("base_risk_penalty", sa.Float()), sa.column("base_friction_penalty", sa.Float()),
        sa.column("metadata", json_type), sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(catalog_table, [{
        "id": uuid5(NAMESPACE_URL, f"qora-product:{product_id}"), "product_id": product_id,
        "section": SECTIONS[product_id], "display_name": product_id.replace("_", " ").title(),
        "is_active": True, "rag_ready": False, "compliance_flag": "REVIEW", "restrictions": {},
        "base_risk_penalty": 0.0, "base_friction_penalty": 0.0,
        "metadata": {"activation_note": "Requires verified published RAG content and compliance clearance"},
        "created_at": now, "updated_at": now,
    } for product_id in WEIGHTS])
    weight_table = sa.table(
        "qora_product_persona_weights",
        sa.column("id", sa.Uuid()), sa.column("table_version_id", sa.Uuid()),
        sa.column("product_id", sa.String()), sa.column("persona_core", sa.String()), sa.column("weight", sa.Float()),
    )
    op.bulk_insert(weight_table, [{
        "id": uuid5(NAMESPACE_URL, f"qora-weight-v1:{product_id}:{persona}"),
        "table_version_id": version_id, "product_id": product_id, "persona_core": persona, "weight": float(weight),
    } for product_id, persona_weights in WEIGHTS.items() for persona, weight in persona_weights.items()])


def downgrade() -> None:
    op.drop_table("qora_product_persona_weights")
    op.drop_table("qora_product_catalog_items")
    op.drop_table("qora_product_weight_table_versions")
    op.drop_table("qora_qualification_answers")
    op.drop_table("qora_orchestrator_executions")
