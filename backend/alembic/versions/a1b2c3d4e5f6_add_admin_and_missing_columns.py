"""Add is_admin column to users, state_json to discussions, label to provider_credentials

Revision ID: a1b2c3d4e5f6
Revises: 3b5c8a1f6d20
Create Date: 2026-07-23
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: str = "3b5c8a1f6d20"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> Sequence:
    # Add is_admin column to users
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))

    # Add state_json column to discussions (missing from prior migrations)
    op.add_column("discussions", sa.Column("state_json", sa.Text(), nullable=False, server_default=""))

    # Add label column to provider_credentials (missing from prior migrations)
    op.add_column("provider_credentials", sa.Column("label", sa.String(length=100), nullable=True))


def downgrade() -> Sequence:
    op.drop_column("provider_credentials", "label")
    op.drop_column("discussions", "state_json")
    op.drop_column("users", "is_admin")
