"""Add country, currency, date_format to gateway_configs

Revision ID: 20260123_000002
Revises: 20260123_000001
Create Date: 2026-01-23

Adds new required fields for gateway configuration:
- country: ISO 3166-1 alpha-2 country code (e.g., KE, UG, TZ)
- currency: ISO 4217 currency code (e.g., KES, USD, UGX)
- date_format: Expected date format for gateway files (default: YYYY-MM-DD)

Also migrates existing charge_keywords from uppercase to lowercase for
case-insensitive matching.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260123_000002'
down_revision = '20260123_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns as nullable first
    op.add_column(
        'gateway_configs',
        sa.Column('country', sa.String(2), nullable=True)
    )
    op.add_column(
        'gateway_configs',
        sa.Column('currency', sa.String(3), nullable=True)
    )
    op.add_column(
        'gateway_configs',
        sa.Column('date_format', sa.String(20), nullable=True)
    )

    # Populate existing rows with defaults (Kenya/KES as default)
    op.execute(
        """
        UPDATE gateway_configs
        SET country = 'KE',
            currency = 'KES',
            date_format = 'YYYY-MM-DD'
        WHERE country IS NULL
        """
    )

    # Migrate charge_keywords to lowercase
    # MySQL JSON values need special handling - using JSON_UNQUOTE and LOWER
    op.execute(
        """
        UPDATE gateway_configs
        SET charge_keywords = LOWER(charge_keywords)
        WHERE charge_keywords IS NOT NULL
        """
    )

    # Make columns non-nullable after populating defaults
    op.alter_column('gateway_configs', 'country', nullable=False, existing_type=sa.String(2))
    op.alter_column('gateway_configs', 'currency', nullable=False, existing_type=sa.String(3))
    op.alter_column('gateway_configs', 'date_format', nullable=False, existing_type=sa.String(20))


def downgrade() -> None:
    # Revert charge_keywords to uppercase
    op.execute(
        """
        UPDATE gateway_configs
        SET charge_keywords = UPPER(charge_keywords)
        WHERE charge_keywords IS NOT NULL
        """
    )

    # Drop the new columns
    op.drop_column('gateway_configs', 'date_format')
    op.drop_column('gateway_configs', 'currency')
    op.drop_column('gateway_configs', 'country')
