"""add referral chat translation cache

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-07 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "referral_chat_message_translations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("referral_link_id", sa.Uuid(), nullable=False),
        sa.Column("source_locale", sa.String(length=16), nullable=False),
        sa.Column("target_locale", sa.String(length=16), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["referral_chat_messages.id"]),
        sa.ForeignKeyConstraint(["referral_link_id"], ["referral_links.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "target_locale", name="uq_referral_chat_message_translation_locale"),
    )
    op.create_index(
        op.f("ix_referral_chat_message_translations_message_id"),
        "referral_chat_message_translations",
        ["message_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_referral_chat_message_translations_referral_link_id"),
        "referral_chat_message_translations",
        ["referral_link_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_referral_chat_message_translations_referral_link_id"),
        table_name="referral_chat_message_translations",
    )
    op.drop_index(
        op.f("ix_referral_chat_message_translations_message_id"),
        table_name="referral_chat_message_translations",
    )
    op.drop_table("referral_chat_message_translations")
