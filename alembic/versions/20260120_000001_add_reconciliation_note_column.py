"""Add reconciliation_note column for system reconciled tracking

Revision ID: 002_reconciliation_note
Revises: 001_batch_audit
Create Date: 2026-01-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_reconciliation_note'
down_revision: Union[str, None] = '001_batch_audit'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add reconciliation_note column to transactions table
    # This column stores:
    # - "System Reconciled" for auto-matched transactions (matched by Transaction ID and Amount)
    # - Custom notes for manually reconciled transactions (copies from manual_recon_note)
    op.add_column(
        'transactions',
        sa.Column('reconciliation_note', sa.String(1000), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('transactions', 'reconciliation_note')
