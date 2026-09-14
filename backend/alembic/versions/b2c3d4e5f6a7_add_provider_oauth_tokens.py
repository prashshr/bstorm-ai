"""Add provider OAuth token vault

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'provider_oauth_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=False),
        sa.Column('access_encrypted', sa.Text(), nullable=False, server_default=''),
        sa.Column('refresh_encrypted', sa.Text(), nullable=False, server_default=''),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('account', sa.String(length=255), nullable=True),
        sa.Column('scopes', sa.String(length=500), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'provider', name='uq_user_oauth_provider'),
    )
    op.create_index('ix_provider_oauth_tokens_user_id', 'provider_oauth_tokens', ['user_id'])
    op.create_index('ix_provider_oauth_tokens_provider', 'provider_oauth_tokens', ['provider'])


def downgrade() -> None:
    op.drop_index('ix_provider_oauth_tokens_provider', table_name='provider_oauth_tokens')
    op.drop_index('ix_provider_oauth_tokens_user_id', table_name='provider_oauth_tokens')
    op.drop_table('provider_oauth_tokens')
