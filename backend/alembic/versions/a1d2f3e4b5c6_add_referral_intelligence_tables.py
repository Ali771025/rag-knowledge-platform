"""add referral intelligence tables

Revision ID: a1d2f3e4b5c6
Revises: f2c4d6e8a1b0
Create Date: 2026-06-05 14:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1d2f3e4b5c6"
down_revision: Union[str, None] = "f2c4d6e8a1b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "referral_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("invite_code", sa.String(length=64), nullable=False),
        sa.Column("short_url", sa.String(length=2048), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=False),
        sa.Column("is_customized", sa.Boolean(), nullable=False),
        sa.Column("latest_status", sa.String(length=64), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("chat_enabled", sa.Boolean(), nullable=False),
        sa.Column("personalization_profile", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_referral_links_owner_user_id"), "referral_links", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_referral_links_invite_code"), "referral_links", ["invite_code"], unique=True)

    op.create_table(
        "referral_progress_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("referral_link_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["referral_link_id"], ["referral_links.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_referral_progress_events_referral_link_id"),
        "referral_progress_events",
        ["referral_link_id"],
        unique=False,
    )

    op.create_table(
        "referral_chat_threads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("referral_link_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("invitee_display_name", sa.String(length=120), nullable=True),
        sa.Column("invitee_wallet_address", sa.String(length=128), nullable=True),
        sa.Column("latest_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["referral_link_id"], ["referral_links.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("referral_link_id"),
    )
    op.create_index(
        op.f("ix_referral_chat_threads_referral_link_id"),
        "referral_chat_threads",
        ["referral_link_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_referral_chat_threads_owner_user_id"),
        "referral_chat_threads",
        ["owner_user_id"],
        unique=False,
    )

    op.create_table(
        "referral_chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("referral_link_id", sa.Uuid(), nullable=False),
        sa.Column("sender_role", sa.String(length=32), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_language", sa.String(length=16), nullable=True),
        sa.Column("target_language", sa.String(length=16), nullable=True),
        sa.Column("translated_text", sa.Text(), nullable=True),
        sa.Column("translation_provider", sa.String(length=64), nullable=True),
        sa.Column("translation_confidence", sa.Float(), nullable=True),
        sa.Column("translation_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("is_read_by_owner", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["referral_link_id"], ["referral_links.id"]),
        sa.ForeignKeyConstraint(["thread_id"], ["referral_chat_threads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_referral_chat_messages_thread_id"), "referral_chat_messages", ["thread_id"], unique=False)
    op.create_index(
        op.f("ix_referral_chat_messages_referral_link_id"),
        "referral_chat_messages",
        ["referral_link_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_referral_chat_messages_referral_link_id"), table_name="referral_chat_messages")
    op.drop_index(op.f("ix_referral_chat_messages_thread_id"), table_name="referral_chat_messages")
    op.drop_table("referral_chat_messages")

    op.drop_index(op.f("ix_referral_chat_threads_owner_user_id"), table_name="referral_chat_threads")
    op.drop_index(op.f("ix_referral_chat_threads_referral_link_id"), table_name="referral_chat_threads")
    op.drop_table("referral_chat_threads")

    op.drop_index(
        op.f("ix_referral_progress_events_referral_link_id"),
        table_name="referral_progress_events",
    )
    op.drop_table("referral_progress_events")

    op.drop_index(op.f("ix_referral_links_invite_code"), table_name="referral_links")
    op.drop_index(op.f("ix_referral_links_owner_user_id"), table_name="referral_links")
    op.drop_table("referral_links")
