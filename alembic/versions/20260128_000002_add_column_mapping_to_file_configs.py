"""Add column_mapping to gateway_file_configs

Revision ID: 20260128_000002
Revises: 20260128_000001
Create Date: 2026-01-28

Adds column_mapping field to gateway_file_configs table for mapping
raw file columns to template columns during file transformation.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20260128_000002'
down_revision = '20260128_000001'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Add column_mapping to gateway_file_configs if it doesn't exist
    # This JSON column stores mapping from template columns to possible source column names
    # Example: {"Date": ["Transaction Date", "Trans Date"], "Reference": ["Ref No", "TXN_ID"]}
    if not column_exists('gateway_file_configs', 'column_mapping'):
        op.add_column(
            'gateway_file_configs',
            sa.Column(
                'column_mapping',
                sa.JSON(),
                nullable=True,
                comment='Mapping from template columns to possible raw column names'
            )
        )


def downgrade() -> None:
    if column_exists('gateway_file_configs', 'column_mapping'):
        op.drop_column('gateway_file_configs', 'column_mapping')
