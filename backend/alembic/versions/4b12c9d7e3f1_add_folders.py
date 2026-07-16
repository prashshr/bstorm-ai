"""Add folders and folder_discussions tables

Revision ID: 4b12c9d7e3f1
Revises: 3a05a68a2500
Create Date: 2026-07-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b12c9d7e3f1'
down_revision: Union[str, Sequence[str], None] = '3a05a68a2500'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'folders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_folders_user_id', 'folders', ['user_id'])

    op.create_table(
        'folder_discussions',
        sa.Column('folder_id', sa.Integer(), sa.ForeignKey('folders.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('discussion_id', sa.Integer(), sa.ForeignKey('discussions.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_table('folder_discussions')
    op.drop_index('ix_folders_user_id', table_name='folders')
    op.drop_table('folders')
