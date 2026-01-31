"""Initial schema - create all tables from current models.

This migration creates all tables for a fresh database deployment.
It replaces all previous incremental migrations that assumed tables
already existed from Base.metadata.create_all().

Revision ID: 000_initial_schema
Revises:
Create Date: 2026-01-18
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '000_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables from SQLAlchemy model definitions."""
    from app.database.mysql_configs import Base

    # Import all models to ensure they're registered with Base.metadata
    from app.sqlModels import authEntities  # noqa: F401
    from app.sqlModels import batchEntities  # noqa: F401
    from app.sqlModels import transactionEntities  # noqa: F401
    from app.sqlModels import gatewayEntities  # noqa: F401
    from app.sqlModels import settingsEntities  # noqa: F401

    # Create all tables using the current model definitions
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Drop all tables."""
    from app.database.mysql_configs import Base

    from app.sqlModels import authEntities  # noqa: F401
    from app.sqlModels import batchEntities  # noqa: F401
    from app.sqlModels import transactionEntities  # noqa: F401
    from app.sqlModels import gatewayEntities  # noqa: F401
    from app.sqlModels import settingsEntities  # noqa: F401

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
