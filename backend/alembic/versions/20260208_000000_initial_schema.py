"""Initial schema - create all tables.

Creates all tables for a fresh database deployment.
Tables: users, refresh_tokens, login_sessions, audit_logs,
        reconciliation_runs, uploaded_files, transactions,
        gateways, gateway_file_configs, gateway_change_requests,
        system_settings.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-02-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Settings tables (no FK dependencies on other app tables)
    # =========================================================================

    op.create_table(
        'system_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key', sa.String(100), unique=True, nullable=False, comment='Setting key'),
        sa.Column('value', sa.Text(), nullable=True, comment='Setting value (JSON for complex values)'),
        sa.Column('value_type', sa.String(20), default='string', comment='Type: string, number, boolean, json'),
        sa.Column('description', sa.String(255), nullable=True, comment='Description of this setting'),
        sa.Column('is_editable', sa.Boolean(), default=True, comment='Whether users can edit this setting'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('updated_by_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # =========================================================================
    # Auth tables
    # =========================================================================

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(100), unique=True, nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('mobile_number', sa.String(20), nullable=True),
        sa.Column('role', sa.String(50), nullable=False, server_default='user'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('password_changed_at', sa.DateTime(), nullable=True),
        sa.Column('password_history', sa.JSON(), nullable=True, comment='Last N password hashes to prevent reuse'),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('locked_until', sa.DateTime(), nullable=True, comment='Account locked until this timestamp'),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_role', 'users', ['role'])
    op.create_index('ix_users_status', 'users', ['status'])
    op.create_index('ix_user_role_status', 'users', ['role', 'status'])

    # Add FK from system_settings to users
    op.create_foreign_key('fk_system_settings_updated_by', 'system_settings', 'users', ['updated_by_id'], ['id'], ondelete='SET NULL')

    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('token', sa.String(500), unique=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_refresh_tokens_id', 'refresh_tokens', ['id'])
    op.create_index('ix_refresh_tokens_token', 'refresh_tokens', ['token'], unique=True)
    op.create_index('ix_refresh_token_user_revoked', 'refresh_tokens', ['user_id', 'revoked'])
    op.create_index('ix_refresh_token_expires', 'refresh_tokens', ['expires_at'])

    op.create_table(
        'login_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(255), unique=True, nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('login_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('logged_out_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_login_sessions_id', 'login_sessions', ['id'])
    op.create_index('ix_login_sessions_session_token', 'login_sessions', ['session_token'], unique=True)
    op.create_index('ix_session_user_active', 'login_sessions', ['user_id', 'is_active'])

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('request_path', sa.String(500), nullable=True),
        sa.Column('request_method', sa.String(10), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_user_action', 'audit_logs', ['user_id', 'action'])
    op.create_index('ix_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('ix_audit_created', 'audit_logs', ['created_at'])

    # =========================================================================
    # Reconciliation run and uploaded file tables
    # =========================================================================

    op.create_table(
        'reconciliation_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(100), unique=True, nullable=False),
        sa.Column('gateway', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='completed'),
        sa.Column('total_external', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('total_internal', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('matched', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('unmatched_external', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('unmatched_internal', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('carry_forward_matched', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_reconciliation_runs_id', 'reconciliation_runs', ['id'])
    op.create_index('ix_reconciliation_runs_run_id', 'reconciliation_runs', ['run_id'], unique=True)
    op.create_index('ix_reconciliation_runs_gateway', 'reconciliation_runs', ['gateway'])
    op.create_index('ix_run_gateway_created', 'reconciliation_runs', ['gateway', 'created_at'])
    op.create_index('ix_run_created_by', 'reconciliation_runs', ['created_by_id'])

    op.create_table(
        'uploaded_files',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('gateway', sa.String(50), nullable=False),
        sa.Column('gateway_type', sa.String(20), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('content_type', sa.String(100), nullable=True),
        sa.Column('is_processed', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('uploaded_by_id', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_uploaded_files_id', 'uploaded_files', ['id'])
    op.create_index('ix_uploaded_files_gateway', 'uploaded_files', ['gateway'])
    op.create_index('ix_uploaded_file_gateway_type', 'uploaded_files', ['gateway', 'gateway_type'])
    op.create_index('ix_uploaded_file_uploaded_by', 'uploaded_files', ['uploaded_by_id'])

    # =========================================================================
    # Transaction table
    # =========================================================================

    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('gateway', sa.String(50), nullable=False),
        sa.Column('gateway_type', sa.String(20), nullable=True),
        sa.Column('transaction_type', sa.String(50), nullable=False),
        sa.Column('reconciliation_category', sa.String(30), nullable=True),
        sa.Column('date', sa.DateTime(), nullable=True),
        sa.Column('transaction_id', sa.String(255), nullable=True),
        sa.Column('narrative', sa.String(500), nullable=True),
        sa.Column('debit', sa.Numeric(18, 2), nullable=True),
        sa.Column('credit', sa.Numeric(18, 2), nullable=True),
        sa.Column('reconciliation_status', sa.String(50), nullable=True),
        sa.Column('run_id', sa.String(100), nullable=True),
        sa.Column('reconciliation_note', sa.String(1000), nullable=True),
        sa.Column('reconciliation_key', sa.String(255), nullable=True),
        sa.Column('source_file', sa.String(255), nullable=True),
        sa.Column('is_manually_reconciled', sa.String(10), nullable=True),
        sa.Column('manual_recon_note', sa.String(1000), nullable=True),
        sa.Column('manual_recon_by', sa.Integer(), nullable=True),
        sa.Column('manual_recon_at', sa.DateTime(), nullable=True),
        sa.Column('authorization_status', sa.String(50), nullable=True),
        sa.Column('authorized_by', sa.Integer(), nullable=True),
        sa.Column('authorized_at', sa.DateTime(), nullable=True),
        sa.Column('authorization_note', sa.String(1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['reconciliation_runs.run_id']),
        sa.ForeignKeyConstraint(['manual_recon_by'], ['users.id']),
        sa.ForeignKeyConstraint(['authorized_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reconciliation_key', 'gateway', name='uq_recon_key_gateway'),
    )
    op.create_index('ix_transactions_id', 'transactions', ['id'])
    op.create_index('ix_transactions_gateway', 'transactions', ['gateway'])
    op.create_index('ix_transactions_gateway_type', 'transactions', ['gateway_type'])
    op.create_index('ix_transactions_transaction_type', 'transactions', ['transaction_type'])
    op.create_index('ix_transactions_reconciliation_category', 'transactions', ['reconciliation_category'])
    op.create_index('ix_transactions_transaction_id', 'transactions', ['transaction_id'])
    op.create_index('ix_transactions_reconciliation_status', 'transactions', ['reconciliation_status'])
    op.create_index('ix_transactions_run_id', 'transactions', ['run_id'])
    op.create_index('ix_transactions_reconciliation_key', 'transactions', ['reconciliation_key'])
    op.create_index('ix_transactions_authorization_status', 'transactions', ['authorization_status'])
    op.create_index('ix_gateway_run', 'transactions', ['gateway', 'run_id'])
    op.create_index('ix_gateway_type_run', 'transactions', ['gateway', 'transaction_type', 'run_id'])
    op.create_index('ix_recon_status_run', 'transactions', ['reconciliation_status', 'run_id'])
    op.create_index('ix_auth_status_run', 'transactions', ['authorization_status', 'run_id'])
    op.create_index('ix_recon_key_run', 'transactions', ['reconciliation_key', 'run_id'])
    op.create_index('ix_recon_category_run', 'transactions', ['reconciliation_category', 'run_id'])
    op.create_index('ix_gateway_type_category', 'transactions', ['gateway_type', 'reconciliation_category', 'run_id'])
    op.create_index('ix_txn_gateway_recon_status', 'transactions', ['gateway', 'reconciliation_status'])
    op.create_index('ix_txn_date', 'transactions', ['date'])

    # =========================================================================
    # Gateway tables (unified only - no legacy gateway_configs)
    # =========================================================================

    op.create_table(
        'gateways',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('display_name', sa.String(100), unique=True, nullable=False, comment="Human-readable gateway name"),
        sa.Column('description', sa.Text(), nullable=True, comment='Optional gateway description'),
        sa.Column('currency_code', sa.String(3), nullable=True, comment='ISO 4217 currency code (e.g., KES, USD)'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_gateways_display_name', 'gateways', ['display_name'], unique=True)

    op.create_table(
        'gateway_file_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('gateway_id', sa.Integer(), nullable=False),
        sa.Column('config_type', sa.String(20), nullable=False, comment="'external' or 'internal'"),
        sa.Column('name', sa.String(50), unique=True, nullable=False, comment='Unique config name used in file paths'),
        sa.Column('expected_filetypes', sa.JSON(), nullable=True),
        sa.Column('header_row_config', sa.JSON(), nullable=True),
        sa.Column('end_of_data_signal', sa.String(255), nullable=True, comment='Text that signals end of data'),
        sa.Column('date_format', sa.String(50), nullable=True, comment='Python strftime format string for date parsing'),
        sa.Column('filename_prefix', sa.String(100), nullable=True, comment='Prefix to match uploaded files'),
        sa.Column('charge_keywords', sa.JSON(), nullable=True, comment='Keywords to identify charges'),
        sa.Column('column_mapping', sa.JSON(), nullable=True, comment='Mapping from template columns to raw column names'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['gateway_id'], ['gateways.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gateway_id', 'config_type', name='uq_gateway_config_type'),
    )
    op.create_index('ix_gateway_file_configs_name', 'gateway_file_configs', ['name'], unique=True)
    op.create_index('ix_gateway_file_config_gateway', 'gateway_file_configs', ['gateway_id'])
    op.create_index('ix_gateway_file_config_type', 'gateway_file_configs', ['config_type'])

    op.create_table(
        'gateway_change_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_type', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('unified_gateway_id', sa.Integer(), nullable=True),
        sa.Column('gateway_display_name', sa.String(100), nullable=True),
        sa.Column('proposed_changes', sa.JSON(), nullable=False),
        sa.Column('requested_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['unified_gateway_id'], ['gateways.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['requested_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_gateway_change_status', 'gateway_change_requests', ['status'])
    op.create_index('ix_gateway_change_requested_by', 'gateway_change_requests', ['requested_by_id'])
    op.create_index('ix_gateway_change_created', 'gateway_change_requests', ['created_at'])


def downgrade() -> None:
    op.drop_table('gateway_change_requests')
    op.drop_table('gateway_file_configs')
    op.drop_table('gateways')
    op.drop_table('transactions')
    op.drop_table('uploaded_files')
    op.drop_table('reconciliation_runs')
    op.drop_table('audit_logs')
    op.drop_table('login_sessions')
    op.drop_table('refresh_tokens')
    # Drop FK from system_settings before dropping users
    op.drop_constraint('fk_system_settings_updated_by', 'system_settings', type_='foreignkey')
    op.drop_table('users')
    op.drop_table('system_settings')
