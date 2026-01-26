"""Drop request_note column from gateway_change_requests

Revision ID: 20260123_000003
Revises: 20260123_000002
Create Date: 2026-01-23

The request_note field is no longer used in the gateway change request workflow.
This migration removes the column from the database.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260123_000003'
down_revision = '20260123_000002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('gateway_change_requests', 'request_note')


def downgrade() -> None:
    op.add_column(
        'gateway_change_requests',
        sa.Column('request_note', sa.Text(), nullable=True)
    )
