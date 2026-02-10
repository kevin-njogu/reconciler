"""Add country to gateways, remove filename_prefix from gateway_file_configs.

Revision ID: 002_add_country_remove_prefix
Revises: 001_initial_schema
Create Date: 2026-02-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002_add_country_remove_prefix'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add country column to gateways table
    op.add_column(
        'gateways',
        sa.Column('country', sa.String(100), nullable=True, comment='Country name (e.g., Kenya, Uganda)')
    )

    # Remove filename_prefix column from gateway_file_configs table
    op.drop_column('gateway_file_configs', 'filename_prefix')


def downgrade() -> None:
    # Re-add filename_prefix column to gateway_file_configs
    op.add_column(
        'gateway_file_configs',
        sa.Column('filename_prefix', sa.String(100), nullable=True, comment='Prefix to match uploaded files')
    )

    # Remove country column from gateways
    op.drop_column('gateways', 'country')
