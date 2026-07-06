"""Drop legacy tender deep analysis result

Revision ID: 006
Revises: 005
Create Date: 2026-07-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('tenders', 'deep_analysis_result')


def downgrade():
    op.add_column('tenders', sa.Column('deep_analysis_result', sa.JSON(), nullable=True))
