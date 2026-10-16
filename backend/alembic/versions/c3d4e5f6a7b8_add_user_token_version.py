"""Add users.token_version for access-token revocation

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-16

Access tokens are stateless JWTs, so nothing on the server could invalidate
one before it expired. Every issued token now carries a `token_ver` claim and
the value is compared against this column; bumping it (for example on a
password change) invalidates every previously issued token at once.

Existing rows all start at 1, which is the version old tokens are implicitly
assumed to hold, so this is a no-op for users until their first credential
change.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    op.drop_column('users', 'token_version')
