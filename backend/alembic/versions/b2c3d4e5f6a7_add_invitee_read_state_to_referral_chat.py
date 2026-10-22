"""add invitee read state to referral chat

Revision ID: b2c3d4e5f6a7
Revises: a1d2f3e4b5c6
Create Date: 2026-06-07 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1d2f3e4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "referral_chat_messages",
        sa.Column("is_read_by_invitee", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("referral_chat_messages", "is_read_by_invitee", server_default=None)


def downgrade() -> None:
    op.drop_column("referral_chat_messages", "is_read_by_invitee")
