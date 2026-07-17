"""add refresh tokens table

Revision ID: 3b5c8a1f6d20
Revises: 9c1d4e7f0a22
Create Date: 2026-07-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "3b5c8a1f6d20"
down_revision: str = "9c1d4e7f0a22"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> Sequence:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("sid", sa.String(64), nullable=False),
        sa.Column("device_id", sa.String(128), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Index("ix_refresh_tokens_user_id", "user_id"),
        sa.Index("ix_refresh_tokens_token_hash", "token_hash"),
        sa.Index("ix_refresh_tokens_sid", "sid"),
    )


def downgrade() -> Sequence:
    op.drop_table("refresh_tokens")
