"""Add file_profile column to gateway_configs table.

This column stores parsing instructions for raw bank statement files,
including header row position, columns to skip, sheet selection, etc.

Revision ID: 003_file_profile
Revises: 002_reconciliation_note
Create Date: 2026-01-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import JSON


# revision identifiers, used by Alembic.
revision = '003_file_profile'
down_revision = '002_reconciliation_note'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add file_profile JSON column to gateway_configs
    op.add_column(
        'gateway_configs',
        sa.Column('file_profile', JSON, nullable=True)
    )


def downgrade() -> None:
    op.drop_column('gateway_configs', 'file_profile')
