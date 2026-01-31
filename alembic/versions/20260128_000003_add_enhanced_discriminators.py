"""Add enhanced discriminators to transactions table.

Revision ID: 20260128_000003
Revises: 20260128_000002
Create Date: 2026-01-28

Adds gateway_type and reconciliation_category columns to the transactions table
for enhanced transaction classification and reconciliation logic.

gateway_type: 'external' or 'internal' - identifies the source type
reconciliation_category: 'reconcilable', 'auto_reconciled', 'non_reconcilable'
    - reconcilable: participates in matching (debits, payouts)
    - auto_reconciled: automatically reconciled (deposits, charges)
    - non_reconcilable: stored for record keeping (top_ups, refunds)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260128_000003'
down_revision = '20260128_000002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add gateway_type column
    op.add_column(
        'transactions',
        sa.Column('gateway_type', sa.String(20), nullable=True, index=True)
    )

    # Add reconciliation_category column
    op.add_column(
        'transactions',
        sa.Column('reconciliation_category', sa.String(30), nullable=True, index=True)
    )

    # Add composite indexes for common queries
    op.create_index(
        'ix_recon_category_batch',
        'transactions',
        ['reconciliation_category', 'batch_id']
    )
    op.create_index(
        'ix_gateway_type_category',
        'transactions',
        ['gateway_type', 'reconciliation_category', 'batch_id']
    )

    # Backfill gateway_type based on existing gateway column
    # External gateways end with '_external', internal with '_internal'
    op.execute("""
        UPDATE transactions
        SET gateway_type = CASE
            WHEN gateway LIKE '%_external' THEN 'external'
            WHEN gateway LIKE '%_internal' THEN 'internal'
            ELSE 'external'
        END
        WHERE gateway_type IS NULL
    """)

    # Backfill reconciliation_category based on transaction_type
    # Note: 'credit' transactions will be updated to 'deposit' in a separate migration
    # For now, map existing types to categories
    op.execute("""
        UPDATE transactions
        SET reconciliation_category = CASE
            WHEN transaction_type IN ('debit', 'payout') THEN 'reconcilable'
            WHEN transaction_type IN ('credit', 'deposit', 'charge') THEN 'auto_reconciled'
            WHEN transaction_type IN ('top_up', 'refund') THEN 'non_reconcilable'
            ELSE 'reconcilable'
        END
        WHERE reconciliation_category IS NULL
    """)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_gateway_type_category', table_name='transactions')
    op.drop_index('ix_recon_category_batch', table_name='transactions')

    # Drop columns
    op.drop_column('transactions', 'reconciliation_category')
    op.drop_column('transactions', 'gateway_type')
