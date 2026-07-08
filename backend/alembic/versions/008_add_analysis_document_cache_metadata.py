"""Add analysis document cache metadata

Revision ID: 008
Revises: 007
Create Date: 2026-07-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("analyses")}

    if "documents_hash" not in columns:
        op.add_column("analyses", sa.Column("documents_hash", sa.String(length=64), nullable=True))

    if "source_documents_count" not in columns:
        op.add_column("analyses", sa.Column("source_documents_count", sa.Integer(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("analyses")}

    if "source_documents_count" in columns:
        op.drop_column("analyses", "source_documents_count")

    if "documents_hash" in columns:
        op.drop_column("analyses", "documents_hash")
