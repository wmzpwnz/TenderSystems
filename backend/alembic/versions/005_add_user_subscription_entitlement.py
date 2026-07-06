"""Add user subscription entitlement

Revision ID: 005
Revises: c71aacd8cda6
Create Date: 2026-06-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '005'
down_revision = 'c71aacd8cda6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'users',
        sa.Column(
            'subscription_status',
            sa.String(length=20),
            nullable=False,
            server_default='inactive',
        ),
    )
    op.add_column(
        'users',
        sa.Column('subscription_expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column('users', 'subscription_status', server_default=None)


def downgrade():
    op.drop_column('users', 'subscription_expires_at')
    op.drop_column('users', 'subscription_status')
