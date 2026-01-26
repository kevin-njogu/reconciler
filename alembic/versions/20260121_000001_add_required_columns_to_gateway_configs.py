"""Add required_columns to gateway_configs

Revision ID: 20260121_000001
Revises: 20260120_000002
Create Date: 2026-01-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260121_000001'
down_revision: Union[str, None] = '003_file_profile'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Default required columns
DEFAULT_REQUIRED_COLUMNS = ["Date", "Transaction Id", "Narrative", "Debit", "Credit"]


def upgrade() -> None:
    # Add required_columns column to gateway_configs table
    op.add_column(
        'gateway_configs',
        sa.Column('required_columns', sa.JSON(), nullable=True)
    )

    # Update existing gateways to have default required columns (MySQL JSON syntax)
    op.execute(
        """
        UPDATE gateway_configs
        SET required_columns = '["Date", "Transaction Id", "Narrative", "Debit", "Credit"]'
        WHERE required_columns IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column('gateway_configs', 'required_columns')
