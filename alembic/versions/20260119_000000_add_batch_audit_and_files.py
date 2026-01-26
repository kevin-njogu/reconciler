"""Add batch audit fields and batch_files table

Revision ID: 001_batch_audit
Revises:
Create Date: 2026-01-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_batch_audit'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to batches table
    op.add_column('batches', sa.Column('description', sa.String(500), nullable=True))
    op.add_column('batches', sa.Column('created_by_id', sa.Integer(), nullable=True))
    op.add_column('batches', sa.Column('updated_at', sa.DateTime(),
                                        server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
                                        nullable=False))

    # Add foreign key constraint for created_by_id
    op.create_foreign_key(
        'fk_batches_created_by',
        'batches', 'users',
        ['created_by_id'], ['id']
    )

    # Add indexes for batches
    op.create_index('ix_batch_status_created', 'batches', ['status', 'created_at'])
    op.create_index('ix_batch_created_by', 'batches', ['created_by_id'])

    # Create batch_files table
    op.create_table(
        'batch_files',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.String(100), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('gateway', sa.String(50), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('content_type', sa.String(100), nullable=True),
        sa.Column('uploaded_by_id', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.batch_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id']),
    )

    # Add indexes for batch_files
    op.create_index('ix_batch_files_batch_id', 'batch_files', ['batch_id'])
    op.create_index('ix_batch_file_batch_gateway', 'batch_files', ['batch_id', 'gateway'])
    op.create_index('ix_batch_file_uploaded_by', 'batch_files', ['uploaded_by_id'])


def downgrade() -> None:
    # Drop batch_files table and its indexes
    op.drop_index('ix_batch_file_uploaded_by', 'batch_files')
    op.drop_index('ix_batch_file_batch_gateway', 'batch_files')
    op.drop_index('ix_batch_files_batch_id', 'batch_files')
    op.drop_table('batch_files')

    # Drop indexes from batches
    op.drop_index('ix_batch_created_by', 'batches')
    op.drop_index('ix_batch_status_created', 'batches')

    # Drop foreign key and columns from batches
    op.drop_constraint('fk_batches_created_by', 'batches', type_='foreignkey')
    op.drop_column('batches', 'updated_at')
    op.drop_column('batches', 'created_by_id')
    op.drop_column('batches', 'description')
