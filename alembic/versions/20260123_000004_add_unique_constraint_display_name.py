"""Add unique constraint on display_name

Revision ID: 20260123_000004
Revises: 20260123_000003
Create Date: 2026-01-23

Adds unique constraint on display_name column in gateway_configs table
to prevent duplicate gateway display names.

First fixes any existing duplicates by appending the gateway name to make them unique.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260123_000004'
down_revision = '20260123_000003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, fix any duplicate display_names by appending gateway name
    # This ensures each display_name is unique before adding the constraint
    op.execute("""
        UPDATE gateway_configs g1
        JOIN (
            SELECT display_name
            FROM gateway_configs
            GROUP BY display_name
            HAVING COUNT(*) > 1
        ) duplicates ON g1.display_name = duplicates.display_name
        SET g1.display_name = CONCAT(g1.display_name, ' (', g1.name, ')')
        WHERE g1.id NOT IN (
            SELECT MIN(g2.id)
            FROM (SELECT * FROM gateway_configs) g2
            GROUP BY g2.display_name
        )
    """)

    # Add unique constraint on display_name
    op.create_unique_constraint(
        'uq_gateway_configs_display_name',
        'gateway_configs',
        ['display_name']
    )


def downgrade() -> None:
    # Remove unique constraint
    op.drop_constraint(
        'uq_gateway_configs_display_name',
        'gateway_configs',
        type_='unique'
    )
