"""SKPL Agent extension tables — context management, desktop automation, quotas.

Revision ID: 0002_skpl_extension
Revises: 0001_initial
Create Date: 2026-07-26 12:00:00.000000

Adds 10 tables for the SKPL Agent extension layer:
- Context Management: skpl_anatomy_symbols, skpl_buglogs, skpl_token_ledgers,
  skpl_cerebrum, skpl_session_contexts
- Desktop Automation: skpl_desktop_nodes, skpl_desktop_action_logs,
  skpl_desktop_sessions
- Quota Management: skpl_tenant_quotas, skpl_resource_usage
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002_skpl_extension'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Context Management ──
    op.create_table(
        'skpl_anatomy_symbols',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('symbol_name', sa.String(256), nullable=False),
        sa.Column('symbol_type', sa.String(32), nullable=False),
        sa.Column('language', sa.String(32), nullable=False),
        sa.Column('line_start', sa.Integer(), nullable=False),
        sa.Column('line_end', sa.Integer(), nullable=False),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_symbol', sa.String(256), nullable=True),
        sa.Column('is_exported', sa.Boolean(), default=False),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('hash', sa.String(64), nullable=True),
        sa.Column('scanned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('skpl_anatomy_symbols') as batch:
        batch.create_index('idx_anatomy_file', ['file_path'])
        batch.create_index('idx_anatomy_symbol', ['symbol_name'])
        batch.create_index('idx_anatomy_lang_type', ['language', 'symbol_type'])
        batch.create_index('idx_anatomy_hash', ['hash'])

    op.create_table(
        'skpl_buglogs',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False, index=True),
        sa.Column('agent_id', sa.String(255), nullable=True),
        sa.Column('error_type', sa.String(128), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(1024), nullable=True),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('context_snippet', sa.Text(), nullable=True),
        sa.Column('fingerprint', sa.String(64), nullable=False, index=True),
        sa.Column('duplicate_of', sa.String(255), nullable=True),
        sa.Column('status', sa.String(32), default='open'),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('skpl_buglogs') as batch:
        batch.create_index('idx_buglog_session', ['session_id'])
        batch.create_index('idx_buglog_fingerprint', ['fingerprint'])
        batch.create_index('idx_buglog_status', ['status'])

    op.create_table(
        'skpl_token_ledgers',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False, index=True),
        sa.Column('agent_id', sa.String(255), nullable=True),
        sa.Column('input_tokens', sa.Integer(), default=0),
        sa.Column('output_tokens', sa.Integer(), default=0),
        sa.Column('total_tokens', sa.Integer(), default=0),
        sa.Column('token_budget', sa.Integer(), nullable=True),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=True),
        sa.Column('model_name', sa.String(128), nullable=True),
        sa.Column('provider', sa.String(64), nullable=True),
        sa.Column('is_waste', sa.Boolean(), default=False),
        sa.Column('waste_reason', sa.Text(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('skpl_token_ledgers') as batch:
        batch.create_index('idx_token_session', ['session_id'])
        batch.create_index('idx_token_recorded', ['recorded_at'])
        batch.create_index('idx_token_waste', ['is_waste'])

    op.create_table(
        'skpl_cerebrum',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('agent_id', sa.String(255), nullable=False, index=True),
        sa.Column('key', sa.String(256), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('category', sa.String(64), default='general'),
        sa.Column('confidence', sa.Float(), default=1.0),
        sa.Column('source', sa.String(256), nullable=True),
        sa.Column('ttl_seconds', sa.Integer(), nullable=True),
        sa.Column('access_count', sa.Integer(), default=0),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('skpl_cerebrum') as batch:
        batch.create_index('idx_cerebrum_agent', ['agent_id'])
        batch.create_index('idx_cerebrum_key', ['agent_id', 'key'])
        batch.create_index('idx_cerebrum_category', ['agent_id', 'category'])

    op.create_table(
        'skpl_session_contexts',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('project_root', sa.String(1024), nullable=True),
        sa.Column('active_file', sa.String(1024), nullable=True),
        sa.Column('context_json', sa.Text(), nullable=True),
        sa.Column('total_tokens_used', sa.Integer(), default=0),
        sa.Column('token_budget', sa.Integer(), default=200000),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── Desktop Automation ──
    op.create_table(
        'skpl_desktop_nodes',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('node_id', sa.String(128), nullable=False, unique=True, index=True),
        sa.Column('tenant_id', sa.String(255), nullable=False, index=True),
        sa.Column('name', sa.String(256), nullable=True),
        sa.Column('platform', sa.String(32), nullable=False),
        sa.Column('hostname', sa.String(256), nullable=True),
        sa.Column('capabilities', sa.Text(), default='[]'),
        sa.Column('screen_width', sa.Integer(), nullable=True),
        sa.Column('screen_height', sa.Integer(), nullable=True),
        sa.Column('version', sa.String(32), default='1.0.0'),
        sa.Column('status', sa.String(32), default='offline'),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actions_this_minute', sa.Integer(), default=0),
        sa.Column('total_actions', sa.Integer(), default=0),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('registered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('skpl_desktop_nodes') as batch:
        batch.create_index('idx_desktop_tenant', ['tenant_id'])
        batch.create_index('idx_desktop_status', ['status'])
        batch.create_index('idx_desktop_heartbeat', ['last_heartbeat'])

    op.create_table(
        'skpl_desktop_action_logs',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('node_id', sa.String(128), nullable=False, index=True),
        sa.Column('session_id', sa.String(255), nullable=False, index=True),
        sa.Column('command_id', sa.String(255), nullable=False, unique=True),
        sa.Column('action', sa.String(64), nullable=False),
        sa.Column('params_json', sa.Text(), nullable=True),
        sa.Column('status', sa.String(32), default='pending'),
        sa.Column('result_json', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('screenshot_path', sa.String(1024), nullable=True),
        sa.Column('grounding_used', sa.Boolean(), default=False),
        sa.Column('grounding_model', sa.String(128), nullable=True),
        sa.Column('target_x', sa.Integer(), nullable=True),
        sa.Column('target_y', sa.Integer(), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('skpl_desktop_action_logs') as batch:
        batch.create_index('idx_desktop_action_node', ['node_id'])
        batch.create_index('idx_desktop_action_session', ['session_id'])
        batch.create_index('idx_desktop_action_status', ['status'])
        batch.create_index('idx_desktop_action_requested', ['requested_at'])

    op.create_table(
        'skpl_desktop_sessions',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('agent_session_id', sa.String(255), nullable=False, index=True),
        sa.Column('node_id', sa.String(128), nullable=False, index=True),
        sa.Column('status', sa.String(32), default='active'),
        sa.Column('total_actions', sa.Integer(), default=0),
        sa.Column('successful_actions', sa.Integer(), default=0),
        sa.Column('failed_actions', sa.Integer(), default=0),
        sa.Column('screenshot_count', sa.Integer(), default=0),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('skpl_desktop_sessions') as batch:
        batch.create_index('idx_desktop_sess_agent', ['agent_session_id'])
        batch.create_index('idx_desktop_sess_node', ['node_id'])
        batch.create_index('idx_desktop_sess_status', ['status'])

    # ── Quota Management ──
    op.create_table(
        'skpl_tenant_quotas',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('max_agents', sa.Integer(), default=10),
        sa.Column('max_sessions', sa.Integer(), default=50),
        sa.Column('max_workspaces', sa.Integer(), default=5),
        sa.Column('max_desktop_nodes', sa.Integer(), default=3),
        sa.Column('max_desktop_actions_per_minute', sa.Integer(), default=60),
        sa.Column('max_web_requests_per_day', sa.Integer(), default=10000),
        sa.Column('max_web_requests_per_minute', sa.Integer(), default=30),
        sa.Column('max_token_budget', sa.Integer(), default=1000000),
        sa.Column('max_tokens_per_request', sa.Integer(), default=100000),
        sa.Column('max_storage_mb', sa.Integer(), default=1024),
        sa.Column('max_file_size_mb', sa.Integer(), default=50),
        sa.Column('max_anatomy_symbols', sa.Integer(), default=100000),
        sa.Column('max_buglog_entries', sa.Integer(), default=10000),
        sa.Column('max_api_requests_per_minute', sa.Integer(), default=100),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'skpl_resource_usage',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False, index=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('active_agents', sa.Integer(), default=0),
        sa.Column('active_sessions', sa.Integer(), default=0),
        sa.Column('active_workspaces', sa.Integer(), default=0),
        sa.Column('registered_desktop_nodes', sa.Integer(), default=0),
        sa.Column('web_requests_today', sa.Integer(), default=0),
        sa.Column('tokens_used_today', sa.Integer(), default=0),
        sa.Column('desktop_actions_today', sa.Integer(), default=0),
        sa.Column('api_requests_today', sa.Integer(), default=0),
        sa.Column('storage_used_mb', sa.Float(), default=0.0),
        sa.Column('anatomy_symbols_count', sa.Integer(), default=0),
        sa.Column('buglog_entries_count', sa.Integer(), default=0),
        sa.Column('last_daily_reset', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('skpl_resource_usage') as batch:
        batch.create_index('idx_usage_tenant', ['tenant_id'])


def downgrade() -> None:
    with op.batch_alter_table('skpl_resource_usage') as batch:
        batch.drop_index('idx_usage_tenant')
    op.drop_table('skpl_resource_usage')
    op.drop_table('skpl_tenant_quotas')

    with op.batch_alter_table('skpl_desktop_sessions') as batch:
        batch.drop_index('idx_desktop_sess_status')
        batch.drop_index('idx_desktop_sess_node')
        batch.drop_index('idx_desktop_sess_agent')
    op.drop_table('skpl_desktop_sessions')

    with op.batch_alter_table('skpl_desktop_action_logs') as batch:
        batch.drop_index('idx_desktop_action_requested')
        batch.drop_index('idx_desktop_action_status')
        batch.drop_index('idx_desktop_action_session')
        batch.drop_index('idx_desktop_action_node')
    op.drop_table('skpl_desktop_action_logs')

    with op.batch_alter_table('skpl_desktop_nodes') as batch:
        batch.drop_index('idx_desktop_heartbeat')
        batch.drop_index('idx_desktop_status')
        batch.drop_index('idx_desktop_tenant')
    op.drop_table('skpl_desktop_nodes')

    op.drop_table('skpl_session_contexts')

    with op.batch_alter_table('skpl_cerebrum') as batch:
        batch.drop_index('idx_cerebrum_category')
        batch.drop_index('idx_cerebrum_key')
        batch.drop_index('idx_cerebrum_agent')
    op.drop_table('skpl_cerebrum')

    with op.batch_alter_table('skpl_token_ledgers') as batch:
        batch.drop_index('idx_token_waste')
        batch.drop_index('idx_token_recorded')
        batch.drop_index('idx_token_session')
    op.drop_table('skpl_token_ledgers')

    with op.batch_alter_table('skpl_buglogs') as batch:
        batch.drop_index('idx_buglog_status')
        batch.drop_index('idx_buglog_fingerprint')
        batch.drop_index('idx_buglog_session')
    op.drop_table('skpl_buglogs')

    with op.batch_alter_table('skpl_anatomy_symbols') as batch:
        batch.drop_index('idx_anatomy_hash')
        batch.drop_index('idx_anatomy_lang_type')
        batch.drop_index('idx_anatomy_symbol')
        batch.drop_index('idx_anatomy_file')
    op.drop_table('skpl_anatomy_symbols')