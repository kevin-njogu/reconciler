"""Add reconciliation_key and source_file columns to transactions

Revision ID: 20260125_000001
Revises: 20260124_000002
Create Date: 2026-01-25

Changes:
- Add reconciliation_key column for storing generated match keys
- Add source_file column for tracking source file of each transaction
- Add index on reconciliation_key for efficient lookups
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260125_000001'
down_revision = '20260124_000002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add reconciliation_key column
    op.add_column(
        'transactions',
        sa.Column('reconciliation_key', sa.String(255), nullable=True)
    )

    # Add source_file column
    op.add_column(
        'transactions',
        sa.Column('source_file', sa.String(255), nullable=True)
    )

    # Add index on reconciliation_key for efficient lookups
    op.create_index(
        'ix_transactions_reconciliation_key',
        'transactions',
        ['reconciliation_key']
    )

    # Add composite index for reconciliation key + batch
    op.create_index(
        'ix_transactions_recon_key_batch',
        'transactions',
        ['reconciliation_key', 'batch_id']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_transactions_recon_key_batch', table_name='transactions')
    op.drop_index('ix_transactions_reconciliation_key', table_name='transactions')

    # Drop columns
    op.drop_column('transactions', 'source_file')
    op.drop_column('transactions', 'reconciliation_key')
