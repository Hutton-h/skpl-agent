"""SKPL Agent — add auth, organization tables and missing columns.

Revision ID: 0003_auth_org
Revises: 0002_skpl_extension
Create Date: 2026-08-10 21:30:00.000000

Adds:
- ``users`` table for JWT authentication
- ``organizations`` table for team management
- ``org_members`` table for org membership
- ``knowledge_bases``: missing org_id, visibility, is_public columns
- ``sessions``: missing device_id column
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0003_auth_org'
down_revision: Union[str, None] = '0002_skpl_extension'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users table ──
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('role', sa.String(20), nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('users') as batch:
        batch.create_index('ix_users_username', ['username'], unique=True)

    # ── organizations table ──
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.String(2000), nullable=True),
        sa.Column('owner_id', sa.String(36), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('organizations') as batch:
        batch.create_index('ix_organizations_name', ['name'], unique=True)
        batch.create_index('idx_org_owner', ['owner_id'])
        batch.create_index('idx_org_active', ['is_active'])

    # ── org_members table ──
    op.create_table(
        'org_members',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('org_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='member'),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('org_members') as batch:
        batch.create_index('idx_org_member_org', ['org_id'])
        batch.create_index('idx_org_member_user', ['user_id'])
        batch.create_index('idx_org_member_unique', ['org_id', 'user_id'], unique=True)

    # ── knowledge_bases: add missing columns ──
    with op.batch_alter_table('knowledge_bases') as batch:
        batch.add_column(sa.Column('org_id', sa.String(255), nullable=True))
        batch.add_column(sa.Column('visibility', sa.String(16), nullable=False, server_default='private'))
        batch.add_column(sa.Column('is_public', sa.Integer(), nullable=False, server_default='0'))
        batch.create_index('ix_knowledge_bases_org_id', ['org_id'])

    # ── sessions: add missing device_id column ──
    with op.batch_alter_table('sessions') as batch:
        batch.add_column(sa.Column('device_id', sa.String(128), nullable=True))
        batch.create_index('ix_sessions_device_id', ['device_id'])


def downgrade() -> None:
    # ── sessions: remove device_id ──
    with op.batch_alter_table('sessions') as batch:
        batch.drop_index('ix_sessions_device_id')
        batch.drop_column('device_id')

    # ── knowledge_bases: remove org columns ──
    with op.batch_alter_table('knowledge_bases') as batch:
        batch.drop_index('ix_knowledge_bases_org_id')
        batch.drop_column('is_public')
        batch.drop_column('visibility')
        batch.drop_column('org_id')

    # ── org_members table ──
    with op.batch_alter_table('org_members') as batch:
        batch.drop_index('idx_org_member_unique')
        batch.drop_index('idx_org_member_user')
        batch.drop_index('idx_org_member_org')
    op.drop_table('org_members')

    # ── organizations table ──
    with op.batch_alter_table('organizations') as batch:
        batch.drop_index('idx_org_active')
        batch.drop_index('idx_org_owner')
        batch.drop_index('ix_organizations_name')
    op.drop_table('organizations')

    # ── users table ──
    with op.batch_alter_table('users') as batch:
        batch.drop_index('ix_users_username')
    op.drop_table('users')