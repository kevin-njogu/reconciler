"""Remove file_profile and required_columns from gateway_configs

Revision ID: 20260123_000001
Revises: 20260121_000001
Create Date: 2026-01-23

Simplifies gateway configuration by removing:
- file_profile: Was used for parsing raw bank statements
- required_columns: Was used for dynamic template columns per gateway

The system now uses a single unified template with fixed columns:
Date, Transaction Id, Narrative, Debit, Credit
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '20260123_000001'
down_revision = '20260121_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove file_profile and required_columns columns from gateway_configs
    op.drop_column('gateway_configs', 'file_profile')
    op.drop_column('gateway_configs', 'required_columns')


def downgrade() -> None:
    # Re-add the columns if needed to rollback
    op.add_column(
        'gateway_configs',
        sa.Column('required_columns', mysql.JSON(), nullable=True)
    )
    op.add_column(
        'gateway_configs',
        sa.Column('file_profile', mysql.JSON(), nullable=True)
    )
