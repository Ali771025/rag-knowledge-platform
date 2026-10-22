"""add rag configurations table

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-05-24 22:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2b3c4d5e6f7a"
down_revision: Union[str, None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_configurations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=False),
        sa.Column("chunk_overlap", sa.Integer(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("similarity_threshold", sa.Float(), nullable=False),
        sa.Column("reranker_enabled", sa.Boolean(), nullable=False),
        sa.Column("hybrid_search_enabled", sa.Boolean(), nullable=False),
        sa.Column("graph_enhanced_retrieval_enabled", sa.Boolean(), nullable=False),
        sa.Column("embedding_model", sa.String(length=128), nullable=False),
        sa.Column("reranker_model", sa.String(length=255), nullable=False),
        sa.Column("vector_collection_name", sa.String(length=255), nullable=False),
        sa.Column("default_labels", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("rag_configurations")
