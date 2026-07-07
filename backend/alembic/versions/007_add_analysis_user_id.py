"""Add user scope to analyses

Revision ID: 007
Revises: 006
Create Date: 2026-07-06 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("analyses")}
    indexes = {index["name"] for index in inspector.get_indexes("analyses")}
    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("analyses")}

    if "user_id" not in columns:
        op.add_column("analyses", sa.Column("user_id", sa.Integer(), nullable=True))

    if "ix_analyses_user_id" not in indexes:
        op.create_index("ix_analyses_user_id", "analyses", ["user_id"], unique=False)

    if "analyses_user_id_fkey" not in foreign_keys:
        op.create_foreign_key(
            "analyses_user_id_fkey",
            "analyses",
            "users",
            ["user_id"],
            ["id"],
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("analyses")}
    indexes = {index["name"] for index in inspector.get_indexes("analyses")}
    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("analyses")}

    if "analyses_user_id_fkey" in foreign_keys:
        op.drop_constraint("analyses_user_id_fkey", "analyses", type_="foreignkey")

    if "ix_analyses_user_id" in indexes:
        op.drop_index("ix_analyses_user_id", table_name="analyses")

    if "user_id" in columns:
        op.drop_column("analyses", "user_id")
