"""add observability log tables

Revision ID: 9f1de6a3c210
Revises: 4c4b9f0d5e9a
Create Date: 2026-05-11 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f1de6a3c210"
down_revision: Union[str, None] = "4c4b9f0d5e9a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("operation_name", sa.String(length=128), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("total_cost", sa.Numeric(precision=18, scale=9), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversation_logs_user_id"), "conversation_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_conversation_logs_created_at"), "conversation_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_conversation_logs_trace_id"), "conversation_logs", ["trace_id"], unique=False)
    op.create_index(op.f("ix_conversation_logs_state"), "conversation_logs", ["state"], unique=False)
    op.create_index(op.f("ix_conversation_logs_session_id"), "conversation_logs", ["session_id"], unique=False)
    op.create_index(op.f("ix_conversation_logs_conversation_id"), "conversation_logs", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_conversation_logs_request_id"), "conversation_logs", ["request_id"], unique=False)
    op.create_index(op.f("ix_conversation_logs_category"), "conversation_logs", ["category"], unique=False)

    op.create_table(
        "cost_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("prompt_cost", sa.Numeric(precision=18, scale=9), nullable=False),
        sa.Column("completion_cost", sa.Numeric(precision=18, scale=9), nullable=False),
        sa.Column("cache_cost", sa.Numeric(precision=18, scale=9), nullable=False),
        sa.Column("total_cost", sa.Numeric(precision=18, scale=9), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cost_logs_user_id"), "cost_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_cost_logs_created_at"), "cost_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_cost_logs_trace_id"), "cost_logs", ["trace_id"], unique=False)
    op.create_index(op.f("ix_cost_logs_state"), "cost_logs", ["state"], unique=False)
    op.create_index(op.f("ix_cost_logs_session_id"), "cost_logs", ["session_id"], unique=False)
    op.create_index(op.f("ix_cost_logs_request_id"), "cost_logs", ["request_id"], unique=False)

    op.create_table(
        "session_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interaction_count", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("total_cost", sa.Numeric(precision=18, scale=9), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_session_logs_user_id"), "session_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_session_logs_created_at"), "session_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_session_logs_trace_id"), "session_logs", ["trace_id"], unique=False)
    op.create_index(op.f("ix_session_logs_state"), "session_logs", ["state"], unique=False)
    op.create_index(op.f("ix_session_logs_session_id"), "session_logs", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_session_logs_session_id"), table_name="session_logs")
    op.drop_index(op.f("ix_session_logs_state"), table_name="session_logs")
    op.drop_index(op.f("ix_session_logs_trace_id"), table_name="session_logs")
    op.drop_index(op.f("ix_session_logs_created_at"), table_name="session_logs")
    op.drop_index(op.f("ix_session_logs_user_id"), table_name="session_logs")
    op.drop_table("session_logs")

    op.drop_index(op.f("ix_cost_logs_request_id"), table_name="cost_logs")
    op.drop_index(op.f("ix_cost_logs_session_id"), table_name="cost_logs")
    op.drop_index(op.f("ix_cost_logs_state"), table_name="cost_logs")
    op.drop_index(op.f("ix_cost_logs_trace_id"), table_name="cost_logs")
    op.drop_index(op.f("ix_cost_logs_created_at"), table_name="cost_logs")
    op.drop_index(op.f("ix_cost_logs_user_id"), table_name="cost_logs")
    op.drop_table("cost_logs")

    op.drop_index(op.f("ix_conversation_logs_category"), table_name="conversation_logs")
    op.drop_index(op.f("ix_conversation_logs_request_id"), table_name="conversation_logs")
    op.drop_index(op.f("ix_conversation_logs_conversation_id"), table_name="conversation_logs")
    op.drop_index(op.f("ix_conversation_logs_session_id"), table_name="conversation_logs")
    op.drop_index(op.f("ix_conversation_logs_state"), table_name="conversation_logs")
    op.drop_index(op.f("ix_conversation_logs_trace_id"), table_name="conversation_logs")
    op.drop_index(op.f("ix_conversation_logs_created_at"), table_name="conversation_logs")
    op.drop_index(op.f("ix_conversation_logs_user_id"), table_name="conversation_logs")
    op.drop_table("conversation_logs")
