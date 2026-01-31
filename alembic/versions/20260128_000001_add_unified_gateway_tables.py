"""Add unified gateway tables (gateways and gateway_file_configs)

Revision ID: 20260128_000001
Revises: 20260125_000001
Create Date: 2026-01-28

Changes:
- Create new 'gateways' table for unified gateway configuration
- Create new 'gateway_file_configs' table for file-specific settings
- Add gateway_id to gateway_change_requests to link to new gateways table
- Keep gateway_configs for backward compatibility during migration
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20260128_000001'
down_revision = '20260125_000001'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Create gateways table if it doesn't exist
    if not table_exists('gateways'):
        op.create_table(
            'gateways',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('display_name', sa.String(100), nullable=False, unique=True, comment='Human-readable gateway name'),
            sa.Column('description', sa.Text(), nullable=True, comment='Optional gateway description'),
            sa.Column('country_id', sa.Integer(), nullable=True, comment='FK to countries table'),
            sa.Column('currency_id', sa.Integer(), nullable=True, comment='FK to currencies table'),
            sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by_id', sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['country_id'], ['countries.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['currency_id'], ['currencies.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        )
        op.create_index('ix_gateways_display_name', 'gateways', ['display_name'])
        op.create_index('ix_gateways_is_active', 'gateways', ['is_active'])

    # Create gateway_file_configs table if it doesn't exist
    if not table_exists('gateway_file_configs'):
        op.create_table(
            'gateway_file_configs',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('gateway_id', sa.Integer(), nullable=False, comment='FK to gateways table'),
            sa.Column('config_type', sa.String(20), nullable=False, comment="'external' or 'internal'"),
            sa.Column('name', sa.String(50), nullable=False, unique=True, comment='Unique config name used in file paths'),
            sa.Column('filename_prefix', sa.String(100), nullable=True, comment='Prefix to match uploaded files'),
            sa.Column('expected_filetypes', sa.JSON(), nullable=True, comment='List of expected file types'),
            sa.Column('header_row_config', sa.JSON(), nullable=True, comment='Rows to skip to reach headers per filetype'),
            sa.Column('end_of_data_signal', sa.String(255), nullable=True, comment='Optional text that signals end of data'),
            sa.Column('date_format_id', sa.Integer(), nullable=True, comment='FK to date_formats table'),
            sa.Column('charge_keywords', sa.JSON(), nullable=True, comment='Keywords to identify charges (external only)'),
            sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['gateway_id'], ['gateways.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['date_format_id'], ['date_formats.id'], ondelete='SET NULL'),
            sa.UniqueConstraint('gateway_id', 'config_type', name='uq_gateway_config_type'),
        )
        op.create_index('ix_gateway_file_configs_name', 'gateway_file_configs', ['name'])
        op.create_index('ix_gateway_file_config_gateway', 'gateway_file_configs', ['gateway_id'])
        op.create_index('ix_gateway_file_config_type', 'gateway_file_configs', ['config_type'])

    # Add unified_gateway_id column to gateway_change_requests if it doesn't exist
    if not column_exists('gateway_change_requests', 'unified_gateway_id'):
        op.add_column(
            'gateway_change_requests',
            sa.Column('unified_gateway_id', sa.Integer(), nullable=True, comment='FK to new gateways table')
        )
        op.create_foreign_key(
            'fk_gateway_change_requests_unified_gateway',
            'gateway_change_requests',
            'gateways',
            ['unified_gateway_id'],
            ['id'],
            ondelete='SET NULL'
        )

    if not column_exists('gateway_change_requests', 'gateway_display_name'):
        op.add_column(
            'gateway_change_requests',
            sa.Column('gateway_display_name', sa.String(100), nullable=True, comment='Store display name for reference')
        )


def downgrade() -> None:
    # Drop foreign key and columns from gateway_change_requests
    op.drop_constraint('fk_gateway_change_requests_unified_gateway', 'gateway_change_requests', type_='foreignkey')
    op.drop_column('gateway_change_requests', 'gateway_display_name')
    op.drop_column('gateway_change_requests', 'unified_gateway_id')

    # Drop gateway_file_configs table
    op.drop_index('ix_gateway_file_config_type', table_name='gateway_file_configs')
    op.drop_index('ix_gateway_file_config_gateway', table_name='gateway_file_configs')
    op.drop_index('ix_gateway_file_configs_name', table_name='gateway_file_configs')
    op.drop_table('gateway_file_configs')

    # Drop gateways table
    op.drop_index('ix_gateways_is_active', table_name='gateways')
    op.drop_index('ix_gateways_display_name', table_name='gateways')
    op.drop_table('gateways')
