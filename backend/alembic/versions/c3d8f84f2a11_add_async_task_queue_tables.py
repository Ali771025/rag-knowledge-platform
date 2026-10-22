"""add async task queue bookkeeping tables

Revision ID: c3d8f84f2a11
Revises: 9f1de6a3c210
Create Date: 2026-05-12 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d8f84f2a11"
down_revision: Union[str, None] = "9f1de6a3c210"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("queue_name", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_logs_task_id"), "task_logs", ["task_id"], unique=False)
    op.create_index(op.f("ix_task_logs_status"), "task_logs", ["status"], unique=False)
    op.create_index(op.f("ix_task_logs_created_at"), "task_logs", ["created_at"], unique=False)

    op.create_table(
        "document_processing_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("embedding_status", sa.String(length=32), nullable=False),
        sa.Column("graph_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_processing_jobs_document_id"),
        "document_processing_jobs",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_processing_jobs_processing_status"),
        "document_processing_jobs",
        ["processing_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_processing_jobs_embedding_status"),
        "document_processing_jobs",
        ["embedding_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_processing_jobs_graph_status"),
        "document_processing_jobs",
        ["graph_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_processing_jobs_created_at"),
        "document_processing_jobs",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "memory_summaries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_memory_summaries_session_id"), "memory_summaries", ["session_id"], unique=False)
    op.create_index(op.f("ix_memory_summaries_created_at"), "memory_summaries", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_memory_summaries_created_at"), table_name="memory_summaries")
    op.drop_index(op.f("ix_memory_summaries_session_id"), table_name="memory_summaries")
    op.drop_table("memory_summaries")

    op.drop_index(op.f("ix_document_processing_jobs_created_at"), table_name="document_processing_jobs")
    op.drop_index(op.f("ix_document_processing_jobs_graph_status"), table_name="document_processing_jobs")
    op.drop_index(op.f("ix_document_processing_jobs_embedding_status"), table_name="document_processing_jobs")
    op.drop_index(op.f("ix_document_processing_jobs_processing_status"), table_name="document_processing_jobs")
    op.drop_index(op.f("ix_document_processing_jobs_document_id"), table_name="document_processing_jobs")
    op.drop_table("document_processing_jobs")

    op.drop_index(op.f("ix_task_logs_created_at"), table_name="task_logs")
    op.drop_index(op.f("ix_task_logs_status"), table_name="task_logs")
    op.drop_index(op.f("ix_task_logs_task_id"), table_name="task_logs")
    op.drop_table("task_logs")
