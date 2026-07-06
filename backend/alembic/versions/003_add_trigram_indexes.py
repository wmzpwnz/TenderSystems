"""Add trigram indexes for autocomplete

Revision ID: 003
Revises: 002
Create Date: 2026-01-05 03:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Включаем расширение pg_trgm для триграмных индексов
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

    # Триграмный индекс для быстрого автодополнения по title
    # Использует similarity для fuzzy matching
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_tenders_title_trgm
        ON tenders
        USING gin(title gin_trgm_ops)
    """)

    # Триграмный индекс для customer_name
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_tenders_customer_name_trgm
        ON tenders
        USING gin(customer_name gin_trgm_ops)
    """)

    print("✓ Триграмные индексы созданы для быстрого автодополнения")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_tenders_title_trgm")
    op.execute("DROP INDEX IF EXISTS ix_tenders_customer_name_trgm")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm CASCADE")
