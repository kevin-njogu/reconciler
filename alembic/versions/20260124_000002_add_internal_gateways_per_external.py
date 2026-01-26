"""Add per-external internal gateways (workpay_equity, workpay_kcb, workpay_mpesa)

Revision ID: 20260124_000002
Revises: 20260124_000001
Create Date: 2026-01-24

Changes:
- Deactivate legacy 'workpay' gateway config
- Add 'workpay_equity', 'workpay_kcb', 'workpay_mpesa' as internal gateways
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '20260124_000002'
down_revision = '20260124_000001'
branch_labels = None
depends_on = None

# New internal gateways to add
NEW_INTERNAL_GATEWAYS = [
    {
        "name": "workpay_equity",
        "gateway_type": "internal",
        "display_name": "Workpay (Equity)",
        "country": "KE",
        "currency": "KES",
        "date_format": "YYYY-MM-DD",
        "charge_keywords": "[]",
        "is_active": True,
    },
    {
        "name": "workpay_kcb",
        "gateway_type": "internal",
        "display_name": "Workpay (KCB)",
        "country": "KE",
        "currency": "KES",
        "date_format": "YYYY-MM-DD",
        "charge_keywords": "[]",
        "is_active": True,
    },
    {
        "name": "workpay_mpesa",
        "gateway_type": "internal",
        "display_name": "Workpay (M-Pesa)",
        "country": "KE",
        "currency": "KES",
        "date_format": "YYYY-MM-DD",
        "charge_keywords": "[]",
        "is_active": True,
    },
]


def upgrade() -> None:
    # Deactivate legacy 'workpay' gateway
    op.execute(
        sa.text(
            "UPDATE gateway_configs SET is_active = 0 WHERE name = 'workpay'"
        )
    )

    # Insert new per-external internal gateways (skip if already exist)
    conn = op.get_bind()
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    for gw in NEW_INTERNAL_GATEWAYS:
        existing = conn.execute(
            sa.text("SELECT id FROM gateway_configs WHERE name = :name"),
            {"name": gw["name"]}
        ).fetchone()

        if not existing:
            conn.execute(
                sa.text(
                    "INSERT INTO gateway_configs "
                    "(name, gateway_type, display_name, country, currency, date_format, "
                    "charge_keywords, is_active, created_at, updated_at) "
                    "VALUES (:name, :gateway_type, :display_name, :country, :currency, "
                    ":date_format, :charge_keywords, :is_active, :created_at, :updated_at)"
                ),
                {
                    **gw,
                    "charge_keywords": gw["charge_keywords"],
                    "is_active": 1,
                    "created_at": now,
                    "updated_at": now,
                }
            )


def downgrade() -> None:
    # Remove the new internal gateways
    op.execute(
        sa.text(
            "DELETE FROM gateway_configs WHERE name IN "
            "('workpay_equity', 'workpay_kcb', 'workpay_mpesa')"
        )
    )

    # Reactivate legacy 'workpay' gateway
    op.execute(
        sa.text(
            "UPDATE gateway_configs SET is_active = 1 WHERE name = 'workpay'"
        )
    )
