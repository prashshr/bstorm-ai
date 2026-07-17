"""add vertex project/region to provider credentials

Revision ID: 7f3a1c9d2e44
Revises: 4b12c9d7e3f1
Create Date: 2026-07-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "7f3a1c9d2e44"
down_revision: str = "4b12c9d7e3f1"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> Sequence:
    op.add_column(
        "provider_credentials",
        sa.Column("project_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "provider_credentials",
        sa.Column("region", sa.String(length=100), nullable=True),
    )


def downgrade() -> Sequence:
    op.drop_column("provider_credentials", "region")
    op.drop_column("provider_credentials", "project_id")
