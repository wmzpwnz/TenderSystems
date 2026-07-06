"""Add performance indexes

Revision ID: 002
Revises: 001
Create Date: 2026-01-03 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Индексы для часто используемых фильтров
    op.create_index('ix_tenders_customer_region', 'tenders', ['customer_region'])
    op.create_index('ix_tenders_publication_date', 'tenders', ['publication_date'])
    op.create_index('ix_tenders_initial_price', 'tenders', ['initial_price'])
    op.create_index('ix_tenders_procedure_type', 'tenders', ['procedure_type'])
    op.create_index('ix_tenders_is_analyzed', 'tenders', ['is_analyzed'])
    op.create_index('ix_tenders_created_at', 'tenders', ['created_at'])

    # Составные индексы для комбинированных запросов
    op.create_index('ix_tenders_status_deadline', 'tenders', ['status', 'application_deadline'])
    op.create_index('ix_tenders_status_price', 'tenders', ['status', 'initial_price'])
    op.create_index('ix_tenders_region_status', 'tenders', ['customer_region', 'status'])

    # GIN индекс для полнотекстового поиска по заголовку (PostgreSQL)
    op.execute("""
        CREATE INDEX ix_tenders_title_gin
        ON tenders
        USING gin(to_tsvector('russian', title))
    """)

    # Индекс для быстрого поиска активных тендеров с близким дедлайном
    op.create_index(
        'ix_tenders_active_urgent',
        'tenders',
        ['status', 'application_deadline'],
        postgresql_where=sa.text("status = 'active' AND application_deadline IS NOT NULL")
    )


def downgrade():
    # Удаляем индексы в обратном порядке
    op.drop_index('ix_tenders_active_urgent', table_name='tenders')

    op.execute('DROP INDEX IF EXISTS ix_tenders_title_gin')

    op.drop_index('ix_tenders_region_status', table_name='tenders')
    op.drop_index('ix_tenders_status_price', table_name='tenders')
    op.drop_index('ix_tenders_status_deadline', table_name='tenders')

    op.drop_index('ix_tenders_created_at', table_name='tenders')
    op.drop_index('ix_tenders_is_analyzed', table_name='tenders')
    op.drop_index('ix_tenders_procedure_type', table_name='tenders')
    op.drop_index('ix_tenders_initial_price', table_name='tenders')
    op.drop_index('ix_tenders_publication_date', table_name='tenders')
    op.drop_index('ix_tenders_customer_region', table_name='tenders')
