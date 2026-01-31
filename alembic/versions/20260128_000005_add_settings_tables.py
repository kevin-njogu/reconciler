"""Add settings tables (date_formats, countries, currencies, reconciliation_keywords, system_settings)

Revision ID: 20260128_000005
Revises: 20260128_000004
Create Date: 2026-01-28

Creates tables for system-wide settings management:
- date_formats: Available date formats for file parsing
- countries: Country configurations
- currencies: Currency configurations (linked to countries)
- reconciliation_keywords: Centralized keywords for auto-reconciliation
- system_settings: Generic key-value settings store
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20260128_000005'
down_revision = '20260128_000004'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Create date_formats table
    if not table_exists('date_formats'):
        op.create_table(
            'date_formats',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('format_string', sa.String(50), nullable=False, unique=True,
                      comment='Python strptime format string'),
            sa.Column('display_name', sa.String(100), nullable=False,
                      comment='Human-readable format name'),
            sa.Column('example', sa.String(50), nullable=False,
                      comment='Example date in this format'),
            sa.Column('is_default', sa.Boolean(), default=False,
                      comment='Whether this is the default format'),
            sa.Column('is_active', sa.Boolean(), default=True,
                      comment='Whether this format is available for selection'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column('created_by_id', sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        )

    # Create countries table
    if not table_exists('countries'):
        op.create_table(
            'countries',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('code', sa.String(3), nullable=False, unique=True,
                      comment='ISO 3166-1 alpha-2 or alpha-3 code'),
            sa.Column('name', sa.String(100), nullable=False,
                      comment='Country name'),
            sa.Column('is_active', sa.Boolean(), default=True,
                      comment='Whether this country is available'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column('created_by_id', sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        )
        op.create_index('ix_country_code', 'countries', ['code'])
        op.create_index('ix_country_active', 'countries', ['is_active'])

    # Create currencies table
    if not table_exists('currencies'):
        op.create_table(
            'currencies',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('code', sa.String(3), nullable=False,
                      comment='ISO 4217 currency code (e.g., USD, KES)'),
            sa.Column('name', sa.String(100), nullable=False,
                      comment='Currency name'),
            sa.Column('symbol', sa.String(10), nullable=True,
                      comment='Currency symbol (e.g., $, KSh)'),
            sa.Column('country_id', sa.Integer(), nullable=False),
            sa.Column('is_default', sa.Boolean(), default=False,
                      comment='Default currency for this country'),
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['country_id'], ['countries.id'], ondelete='CASCADE'),
        )
        op.create_index('ix_currency_code', 'currencies', ['code'])
        op.create_index('ix_currency_country', 'currencies', ['country_id'])

    # Create reconciliation_keywords table
    if not table_exists('reconciliation_keywords'):
        op.create_table(
            'reconciliation_keywords',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('keyword', sa.String(100), nullable=False,
                      comment='The keyword to match in transaction Details'),
            sa.Column('keyword_type', sa.String(20), nullable=False,
                      comment='Type: charge, wallet_topup, reversal'),
            sa.Column('description', sa.String(255), nullable=True,
                      comment='Optional description of what this keyword matches'),
            sa.Column('is_case_sensitive', sa.Boolean(), default=False,
                      comment='Whether matching is case-sensitive'),
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.Column('gateway_id', sa.Integer(), nullable=True,
                      comment='If set, keyword only applies to this gateway'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column('created_by_id', sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['gateway_id'], ['gateway_configs.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        )
        op.create_index('ix_keyword_type', 'reconciliation_keywords', ['keyword_type'])
        op.create_index('ix_keyword_active', 'reconciliation_keywords', ['is_active'])
        op.create_index('ix_keyword_gateway', 'reconciliation_keywords', ['gateway_id'])

    # Create system_settings table
    if not table_exists('system_settings'):
        op.create_table(
            'system_settings',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('key', sa.String(100), nullable=False, unique=True,
                      comment='Setting key'),
            sa.Column('value', sa.Text(), nullable=True,
                      comment='Setting value (JSON for complex values)'),
            sa.Column('value_type', sa.String(20), default='string',
                      comment='Type: string, number, boolean, json'),
            sa.Column('description', sa.String(255), nullable=True,
                      comment='Description of this setting'),
            sa.Column('is_editable', sa.Boolean(), default=True,
                      comment='Whether users can edit this setting'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column('updated_by_id', sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ondelete='SET NULL'),
        )


def downgrade() -> None:
    # Drop tables in reverse order of creation
    if table_exists('system_settings'):
        op.drop_table('system_settings')

    if table_exists('reconciliation_keywords'):
        op.drop_index('ix_keyword_gateway', table_name='reconciliation_keywords')
        op.drop_index('ix_keyword_active', table_name='reconciliation_keywords')
        op.drop_index('ix_keyword_type', table_name='reconciliation_keywords')
        op.drop_table('reconciliation_keywords')

    if table_exists('currencies'):
        op.drop_index('ix_currency_country', table_name='currencies')
        op.drop_index('ix_currency_code', table_name='currencies')
        op.drop_table('currencies')

    if table_exists('countries'):
        op.drop_index('ix_country_active', table_name='countries')
        op.drop_index('ix_country_code', table_name='countries')
        op.drop_table('countries')

    if table_exists('date_formats'):
        op.drop_table('date_formats')
