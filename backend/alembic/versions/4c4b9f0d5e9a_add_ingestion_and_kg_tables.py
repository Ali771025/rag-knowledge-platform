"""add ingestion and knowledge graph tables

Revision ID: 4c4b9f0d5e9a
Revises: d00b82175167
Create Date: 2026-05-05 11:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4c4b9f0d5e9a"
down_revision: Union[str, None] = "d00b82175167"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_uri", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("cleaned_text", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_source_type"), "documents", ["source_type"], unique=False)
    op.create_index(op.f("ix_documents_source_uri"), "documents", ["source_uri"], unique=False)
    op.create_index(op.f("ix_documents_language"), "documents", ["language"], unique=False)
    op.create_index(op.f("ix_documents_content_hash"), "documents", ["content_hash"], unique=False)

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_uri", sa.String(length=2048), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("stats_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ingestion_jobs_source_type"), "ingestion_jobs", ["source_type"], unique=False)
    op.create_index(op.f("ix_ingestion_jobs_source_uri"), "ingestion_jobs", ["source_uri"], unique=False)
    op.create_index(op.f("ix_ingestion_jobs_status"), "ingestion_jobs", ["status"], unique=False)

    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_chunk_document_index"),
    )
    op.create_index(op.f("ix_chunks_document_id"), "chunks", ["document_id"], unique=False)
    op.create_index(op.f("ix_chunks_content_hash"), "chunks", ["content_hash"], unique=False)

    op.create_table(
        "document_metadata",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("subcategory", sa.String(length=255), nullable=True),
        sa.Column("difficulty_level", sa.String(length=64), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("section_type", sa.String(length=128), nullable=True),
        sa.Column("parent_topic", sa.String(length=255), nullable=True),
        sa.Column("related_topics", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_metadata_document_id"), "document_metadata", ["document_id"], unique=False)
    op.create_index(op.f("ix_document_metadata_topic"), "document_metadata", ["topic"], unique=False)
    op.create_index(op.f("ix_document_metadata_category"), "document_metadata", ["category"], unique=False)
    op.create_index(op.f("ix_document_metadata_language"), "document_metadata", ["language"], unique=False)

    op.create_table(
        "knowledge_graph_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
        sa.Column("entity_count", sa.Integer(), nullable=False),
        sa.Column("relation_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_graph_records_document_id"),
        "knowledge_graph_records",
        ["document_id"],
        unique=False,
    )
    op.create_index(op.f("ix_knowledge_graph_records_chunk_id"), "knowledge_graph_records", ["chunk_id"], unique=False)
    op.create_index(op.f("ix_knowledge_graph_records_status"), "knowledge_graph_records", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_knowledge_graph_records_status"), table_name="knowledge_graph_records")
    op.drop_index(op.f("ix_knowledge_graph_records_chunk_id"), table_name="knowledge_graph_records")
    op.drop_index(op.f("ix_knowledge_graph_records_document_id"), table_name="knowledge_graph_records")
    op.drop_table("knowledge_graph_records")

    op.drop_index(op.f("ix_document_metadata_language"), table_name="document_metadata")
    op.drop_index(op.f("ix_document_metadata_category"), table_name="document_metadata")
    op.drop_index(op.f("ix_document_metadata_topic"), table_name="document_metadata")
    op.drop_index(op.f("ix_document_metadata_document_id"), table_name="document_metadata")
    op.drop_table("document_metadata")

    op.drop_index(op.f("ix_chunks_content_hash"), table_name="chunks")
    op.drop_index(op.f("ix_chunks_document_id"), table_name="chunks")
    op.drop_table("chunks")

    op.drop_index(op.f("ix_ingestion_jobs_status"), table_name="ingestion_jobs")
    op.drop_index(op.f("ix_ingestion_jobs_source_uri"), table_name="ingestion_jobs")
    op.drop_index(op.f("ix_ingestion_jobs_source_type"), table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")

    op.drop_index(op.f("ix_documents_content_hash"), table_name="documents")
    op.drop_index(op.f("ix_documents_language"), table_name="documents")
    op.drop_index(op.f("ix_documents_source_uri"), table_name="documents")
    op.drop_index(op.f("ix_documents_source_type"), table_name="documents")
    op.drop_table("documents")
