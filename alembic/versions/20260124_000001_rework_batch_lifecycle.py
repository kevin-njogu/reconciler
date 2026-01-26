"""Rework batch lifecycle - add closed_at, delete requests table, simplify status

Revision ID: 20260124_000001
Revises: 20260123_000004
Create Date: 2026-01-24

Changes:
- Add `closed_at` column to `batches` table
- Drop `updated_at` column from `batches` table
- Make `created_by_id` NOT NULL on `batches` table
- Migrate any 'processing' or 'failed' batch statuses to 'pending'
- Create `batch_delete_requests` table for maker-checker deletion workflow
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '20260124_000001'
down_revision = '20260123_000004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Migrate any non-standard statuses to 'pending'
    op.execute("""
        UPDATE batches
        SET status = 'pending'
        WHERE status NOT IN ('pending', 'completed')
    """)

    # 2. Add closed_at column to batches
    op.add_column('batches', sa.Column('closed_at', sa.DateTime(), nullable=True))

    # 3. Set closed_at for already-completed batches
    op.execute("""
        UPDATE batches
        SET closed_at = created_at
        WHERE status = 'completed' AND closed_at IS NULL
    """)

    # 4. Drop updated_at column from batches
    op.drop_column('batches', 'updated_at')

    # 5. Make created_by_id NOT NULL (set any NULLs to 1 first as fallback)
    op.execute("""
        UPDATE batches
        SET created_by_id = 1
        WHERE created_by_id IS NULL
    """)
    op.alter_column('batches', 'created_by_id',
                    existing_type=sa.Integer(),
                    nullable=False)

    # 6. Create batch_delete_requests table
    op.create_table(
        'batch_delete_requests',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('batch_id', sa.String(100), sa.ForeignKey('batches.batch_id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('reason', sa.String(500), nullable=True),
        sa.Column('requested_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reviewed_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # 7. Create indexes for batch_delete_requests
    op.create_index('ix_batch_delete_request_status', 'batch_delete_requests', ['status'])
    op.create_index('ix_batch_delete_request_batch', 'batch_delete_requests', ['batch_id', 'status'])
    op.create_index('ix_batch_delete_request_requested_by', 'batch_delete_requests', ['requested_by_id'])


def downgrade() -> None:
    # Drop batch_delete_requests table and indexes
    op.drop_index('ix_batch_delete_request_requested_by', table_name='batch_delete_requests')
    op.drop_index('ix_batch_delete_request_batch', table_name='batch_delete_requests')
    op.drop_index('ix_batch_delete_request_status', table_name='batch_delete_requests')
    op.drop_table('batch_delete_requests')

    # Restore created_by_id to nullable
    op.alter_column('batches', 'created_by_id',
                    existing_type=sa.Integer(),
                    nullable=True)

    # Restore updated_at column
    op.add_column('batches', sa.Column('updated_at', sa.DateTime(),
                                        server_default=sa.func.now(),
                                        nullable=False))

    # Drop closed_at column
    op.drop_column('batches', 'closed_at')
