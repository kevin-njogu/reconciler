"""Auth security overhaul: OTP, login sessions, lockout, password history.

Revision ID: 20260131_000001
Revises: 20260130_000001
Create Date: 2026-01-31

Adds columns to users table:
- mobile_number (VARCHAR(20))
- failed_login_attempts (INT, default 0)
- locked_until (DATETIME)
- password_changed_at (DATETIME)
- password_history (JSON)

Creates new tables:
- otp_tokens: OTP storage for 2FA
- login_sessions: Active session tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20260131_000001'
down_revision = '20260130_000001'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    insp = inspect(bind)
    return table_name in insp.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    insp = inspect(bind)
    columns = [c['name'] for c in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # --- Add new columns to users table ---

    if not column_exists('users', 'mobile_number'):
        op.add_column(
            'users',
            sa.Column('mobile_number', sa.String(20), nullable=True)
        )

    if not column_exists('users', 'failed_login_attempts'):
        op.add_column(
            'users',
            sa.Column('failed_login_attempts', sa.Integer(),
                      nullable=False, server_default='0')
        )

    if not column_exists('users', 'locked_until'):
        op.add_column(
            'users',
            sa.Column('locked_until', sa.DateTime(), nullable=True,
                      comment='Account locked until this timestamp')
        )

    if not column_exists('users', 'password_changed_at'):
        op.add_column(
            'users',
            sa.Column('password_changed_at', sa.DateTime(), nullable=True)
        )

    if not column_exists('users', 'password_history'):
        op.add_column(
            'users',
            sa.Column('password_history', sa.JSON(), nullable=True,
                      comment='Last N password hashes to prevent reuse')
        )

    # --- Create otp_tokens table ---

    if not table_exists('otp_tokens'):
        op.create_table(
            'otp_tokens',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('otp_hash', sa.String(255), nullable=False,
                      comment='Bcrypt hash of 6-digit OTP'),
            sa.Column('purpose', sa.String(50), nullable=False,
                      comment='login, welcome, or forgot_password'),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('is_used', sa.Boolean(), nullable=False,
                      server_default='0'),
            sa.Column('used_at', sa.DateTime(), nullable=True),
            sa.Column('attempts', sa.Integer(), nullable=False,
                      server_default='0',
                      comment='Wrong OTP attempts (max 3)'),
            sa.Column('ip_address', sa.String(45), nullable=True),
            sa.Column('user_agent', sa.String(500), nullable=True),
            sa.Column('created_at', sa.DateTime(),
                      server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                    ondelete='CASCADE'),
        )
        op.create_index('ix_otp_user_purpose', 'otp_tokens',
                        ['user_id', 'purpose'])
        op.create_index('ix_otp_expires', 'otp_tokens', ['expires_at'])

    # --- Create login_sessions table ---

    if not table_exists('login_sessions'):
        op.create_table(
            'login_sessions',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('session_token', sa.String(255), unique=True,
                      nullable=False),
            sa.Column('ip_address', sa.String(45), nullable=True),
            sa.Column('user_agent', sa.String(500), nullable=True),
            sa.Column('login_at', sa.DateTime(),
                      server_default=sa.func.now(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False,
                      server_default='1'),
            sa.Column('logged_out_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                    ondelete='CASCADE'),
        )
        op.create_index('ix_session_token', 'login_sessions',
                        ['session_token'], unique=True)
        op.create_index('ix_session_user_active', 'login_sessions',
                        ['user_id', 'is_active'])


def downgrade() -> None:
    # Drop login_sessions
    if table_exists('login_sessions'):
        op.drop_index('ix_session_user_active', table_name='login_sessions')
        op.drop_index('ix_session_token', table_name='login_sessions')
        op.drop_table('login_sessions')

    # Drop otp_tokens
    if table_exists('otp_tokens'):
        op.drop_index('ix_otp_expires', table_name='otp_tokens')
        op.drop_index('ix_otp_user_purpose', table_name='otp_tokens')
        op.drop_table('otp_tokens')

    # Remove user columns
    if column_exists('users', 'password_history'):
        op.drop_column('users', 'password_history')

    if column_exists('users', 'password_changed_at'):
        op.drop_column('users', 'password_changed_at')

    if column_exists('users', 'locked_until'):
        op.drop_column('users', 'locked_until')

    if column_exists('users', 'failed_login_attempts'):
        op.drop_column('users', 'failed_login_attempts')

    if column_exists('users', 'mobile_number'):
        op.drop_column('users', 'mobile_number')
