"""Initial application schema

Revision ID: 001
Revises:
Create Date: 2026-01-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True),
        sa.Column('telegram_chat_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table(
        'tenders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('eis_id', sa.String(length=100), nullable=False),
        sa.Column('number', sa.String(length=100), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('customer_name', sa.String(length=500), nullable=True),
        sa.Column('customer_inn', sa.String(length=20), nullable=True),
        sa.Column('customer_region', sa.String(length=100), nullable=True),
        sa.Column('initial_price', sa.Numeric(15, 2), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('guarantee_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('contract_guarantee', sa.Numeric(15, 2), nullable=True),
        sa.Column('publication_date', sa.DateTime(), nullable=True),
        sa.Column('application_deadline', sa.DateTime(), nullable=True),
        sa.Column('contract_deadline', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('procedure_type', sa.String(length=100), nullable=True),
        sa.Column('documents_url', sa.Text(), nullable=True),
        sa.Column('documents_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('okpd2_codes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('requirements', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('platform', sa.String(length=100), nullable=True),
        sa.Column('prepayment_type', sa.String(length=50), nullable=True),
        sa.Column('preferences', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('is_analyzed', sa.Boolean(), nullable=True),
        sa.Column('deep_analysis_result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tenders_eis_id', 'tenders', ['eis_id'], unique=True)
    op.create_index('ix_tenders_number', 'tenders', ['number'], unique=False)
    op.create_index('ix_tenders_customer_inn', 'tenders', ['customer_inn'], unique=False)
    op.create_index('ix_tenders_application_deadline', 'tenders', ['application_deadline'], unique=False)
    op.create_index('ix_tenders_status', 'tenders', ['status'], unique=False)

    op.create_table(
        'analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tender_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('critical_requirements', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('deadlines', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('financial_info', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('evaluation_criteria', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('risks', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('margin_analysis', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('win_probability', sa.Numeric(5, 2), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=True),
        sa.Column('raw_ai_response', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('analysis_version', sa.String(length=20), nullable=True),
        sa.Column('analysis_type', sa.String(length=20), nullable=True),
        sa.Column('documents_analyzed', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('cost_breakdown', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_analyses_tender_id', 'analyses', ['tender_id'], unique=False)
    op.create_index('ix_analyses_user_id', 'analyses', ['user_id'], unique=False)

    op.create_table(
        'company_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=True),
        sa.Column('inn', sa.String(length=20), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('licenses', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('sro_certificates', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('experience_contracts', sa.Integer(), nullable=True),
        sa.Column('experience_sum', sa.Numeric(15, 2), nullable=True),
        sa.Column('okpd2_codes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('equipment', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_company_profiles_user_id', 'company_profiles', ['user_id'], unique=True)
    op.create_index('ix_company_profiles_inn', 'company_profiles', ['inn'], unique=False)

    op.create_table(
        'user_tenders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('tender_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_tenders_user_id', 'user_tenders', ['user_id'], unique=False)
    op.create_index('ix_user_tenders_tender_id', 'user_tenders', ['tender_id'], unique=False)

    op.create_table(
        'search_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('filters', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('notify_email', sa.Boolean(), nullable=True),
        sa.Column('notify_telegram', sa.Boolean(), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_search_subscriptions_user_id', 'search_subscriptions', ['user_id'], unique=False)


def downgrade():
    op.drop_index('ix_search_subscriptions_user_id', table_name='search_subscriptions')
    op.drop_table('search_subscriptions')
    op.drop_index('ix_user_tenders_tender_id', table_name='user_tenders')
    op.drop_index('ix_user_tenders_user_id', table_name='user_tenders')
    op.drop_table('user_tenders')
    op.drop_index('ix_company_profiles_inn', table_name='company_profiles')
    op.drop_index('ix_company_profiles_user_id', table_name='company_profiles')
    op.drop_table('company_profiles')
    op.drop_index('ix_analyses_user_id', table_name='analyses')
    op.drop_index('ix_analyses_tender_id', table_name='analyses')
    op.drop_table('analyses')
    op.drop_index('ix_tenders_status', table_name='tenders')
    op.drop_index('ix_tenders_application_deadline', table_name='tenders')
    op.drop_index('ix_tenders_customer_inn', table_name='tenders')
    op.drop_index('ix_tenders_number', table_name='tenders')
    op.drop_index('ix_tenders_eis_id', table_name='tenders')
    op.drop_table('tenders')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
