"""add knowledge sources table

Revision ID: 1a2b3c4d5e6f
Revises: 8b9d3f7a1c2e
Create Date: 2026-05-24 21:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "8b9d3f7a1c2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_uri", sa.String(length=2048), nullable=False),
        sa.Column("domain", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("tags_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_chunks", sa.Integer(), nullable=False),
        sa.Column("embedded_chunks", sa.Integer(), nullable=False),
        sa.Column("indexing_completed", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("ingestion_job_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ingestion_job_id"], ["ingestion_jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_knowledge_sources_source_type"), "knowledge_sources", ["source_type"], unique=False)
    op.create_index(op.f("ix_knowledge_sources_source_uri"), "knowledge_sources", ["source_uri"], unique=False)
    op.create_index(op.f("ix_knowledge_sources_domain"), "knowledge_sources", ["domain"], unique=False)
    op.create_index(op.f("ix_knowledge_sources_label"), "knowledge_sources", ["label"], unique=False)
    op.create_index(op.f("ix_knowledge_sources_status"), "knowledge_sources", ["status"], unique=False)
    op.create_index(op.f("ix_knowledge_sources_document_id"), "knowledge_sources", ["document_id"], unique=False)
    op.create_index(op.f("ix_knowledge_sources_ingestion_job_id"), "knowledge_sources", ["ingestion_job_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_knowledge_sources_ingestion_job_id"), table_name="knowledge_sources")
    op.drop_index(op.f("ix_knowledge_sources_document_id"), table_name="knowledge_sources")
    op.drop_index(op.f("ix_knowledge_sources_status"), table_name="knowledge_sources")
    op.drop_index(op.f("ix_knowledge_sources_label"), table_name="knowledge_sources")
    op.drop_index(op.f("ix_knowledge_sources_domain"), table_name="knowledge_sources")
    op.drop_index(op.f("ix_knowledge_sources_source_uri"), table_name="knowledge_sources")
    op.drop_index(op.f("ix_knowledge_sources_source_type"), table_name="knowledge_sources")
    op.drop_table("knowledge_sources")
