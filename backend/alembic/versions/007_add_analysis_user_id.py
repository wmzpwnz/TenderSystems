"""Add user scope to analyses

Revision ID: 007
Revises: 006
Create Date: 2026-07-06 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('analyses', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index('ix_analyses_user_id', 'analyses', ['user_id'], unique=False)
    op.create_foreign_key(
        'analyses_user_id_fkey',
        'analyses',
        'users',
        ['user_id'],
        ['id'],
    )


def downgrade():
    op.drop_constraint('analyses_user_id_fkey', 'analyses', type_='foreignkey')
    op.drop_index('ix_analyses_user_id', table_name='analyses')
    op.drop_column('analyses', 'user_id')
