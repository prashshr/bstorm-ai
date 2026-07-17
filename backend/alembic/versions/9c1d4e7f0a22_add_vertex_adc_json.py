"""add vertex adc json credential

Revision ID: 9c1d4e7f0a22
Revises: 7f3a1c9d2e44
Create Date: 2026-07-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "9c1d4e7f0a22"
down_revision: str = "7f3a1c9d2e44"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> Sequence:
    op.add_column(
        "provider_credentials",
        sa.Column("adc_json_encrypted", sa.Text(), nullable=True),
    )


def downgrade() -> Sequence:
    op.drop_column("provider_credentials", "adc_json_encrypted")
