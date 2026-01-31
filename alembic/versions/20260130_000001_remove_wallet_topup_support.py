"""Remove wallet top-up support from schema.

Revision ID: 20260130_000001
Revises: 20260128_000005
Create Date: 2026-01-30

Removes wallet top-up functionality:
- Drops top_up_keywords column from gateway_file_configs table
- Drops top_up_keywords column from gateway_configs table
- Deletes any reconciliation_keywords rows with keyword_type='wallet_topup'

Wallet top-ups will be handled manually outside the system.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20260130_000001'
down_revision = '20260128_000005'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Drop top_up_keywords from gateway_file_configs (unified system)
    if column_exists('gateway_file_configs', 'top_up_keywords'):
        op.drop_column('gateway_file_configs', 'top_up_keywords')

    # Drop top_up_keywords from gateway_configs (legacy system)
    if column_exists('gateway_configs', 'top_up_keywords'):
        op.drop_column('gateway_configs', 'top_up_keywords')

    # Delete wallet_topup keywords from reconciliation_keywords table
    if table_exists('reconciliation_keywords'):
        op.execute(
            sa.text("DELETE FROM reconciliation_keywords WHERE keyword_type = 'wallet_topup'")
        )


def downgrade() -> None:
    # Re-add top_up_keywords to gateway_file_configs
    if not column_exists('gateway_file_configs', 'top_up_keywords'):
        op.add_column(
            'gateway_file_configs',
            sa.Column('top_up_keywords', sa.JSON, nullable=True,
                      comment="Keywords to identify wallet top-ups (internal gateways only)")
        )

    # Re-add top_up_keywords to gateway_configs
    if not column_exists('gateway_configs', 'top_up_keywords'):
        op.add_column(
            'gateway_configs',
            sa.Column('top_up_keywords', sa.JSON, nullable=True,
                      comment="Keywords to identify wallet top-ups (internal gateways)")
        )

    # Note: Deleted reconciliation_keywords rows cannot be automatically restored.
    # Re-seed defaults via POST /api/v1/settings/seed-defaults if needed.
