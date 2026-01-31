"""Add top_up_keywords column to gateway tables.

Revision ID: 20260128_000004
Revises: 20260128_000003
Create Date: 2026-01-28

Adds top_up_keywords column to gateway_file_configs and gateway_configs tables.
This column stores keywords to identify wallet top-up transactions in internal
statements, similar to how charge_keywords identifies charges in external statements.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260128_000004'
down_revision = '20260128_000003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add top_up_keywords to gateway_file_configs (unified system)
    op.add_column(
        'gateway_file_configs',
        sa.Column('top_up_keywords', sa.JSON, nullable=True,
                  comment="Keywords to identify wallet top-ups (internal gateways only)")
    )

    # Add top_up_keywords to gateway_configs (legacy system, for backward compatibility)
    op.add_column(
        'gateway_configs',
        sa.Column('top_up_keywords', sa.JSON, nullable=True,
                  comment="Keywords to identify wallet top-ups (internal gateways)")
    )


def downgrade() -> None:
    # Remove from gateway_configs (legacy)
    op.drop_column('gateway_configs', 'top_up_keywords')

    # Remove from gateway_file_configs (unified)
    op.drop_column('gateway_file_configs', 'top_up_keywords')
