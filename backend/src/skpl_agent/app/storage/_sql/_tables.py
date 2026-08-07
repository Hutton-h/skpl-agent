"""SQLAlchemy 2.0 declarative tables backing :class:`AsyncSQLAlchemyStorage`.

Every record type maps to one table with the layout:

- ``id`` primary key + ``created_at`` / ``updated_at`` timestamps;
- one column per relational / indexed field promoted from the
  record's top level;
- a single ``payload`` JSON column carrying the remainder of
  ``record.model_dump(mode="json")`` **minus** the promoted columns —
  so no field is ever stored in both places (see the design doc in
  ``_mappers.py`` for the round-trip contract).

Portability constraints — the *schema* intentionally sticks to the
subset of SQLAlchemy that works on every async-capable dialect we
target (SQLite / Postgres / MySQL): plain :class:`~sqlalchemy.JSON`
(never JSONB), no generated columns, no ``FOR UPDATE``.  Atomic
upserts *are* emitted with dialect-native ``ON CONFLICT`` /
``ON DUPLICATE KEY UPDATE`` syntax, but through the explicit
per-dialect dispatch in
:meth:`~agentscope.app.storage.AsyncSQLAlchemyStorage._upsert_stmt`
rather than leaking into the table definitions here.  The messages
table sidesteps the
JSON-record shape because it is inherently list-like — see
:class:`MessageRow` for the shape and the write path in
:class:`~agentscope.app.storage.AsyncSQLAlchemyStorage.upsert_message`.
"""
from datetime import datetime
from typing import Any, ClassVar
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
_ID_LEN = 255

class _Base(DeclarativeBase):
    """Declarative base shared by every table in :mod:`_sql`.

    Kept private because it is an implementation detail: users of
    :class:`~agentscope.app.storage.AsyncSQLAlchemyStorage` never see it.
    """

class _JsonRecordMixin(_Base):
    """Column set common to every ``*Row`` that stores a record payload.

    Concrete tables inherit this mixin plus :class:`_Base`, add their
    own promoted columns, and set two class variables that drive the
    generic mapper in :mod:`_mappers`:

    - ``_record_cls``: the pydantic :class:`_RecordBase` subclass
      this row represents.
    - ``_indexed_fields``: the tuple of top-level record fields that
      live in dedicated columns (and therefore MUST be popped out of
      ``payload`` on write and merged back on read).

    The three envelope columns (``id`` / ``created_at`` /
    ``updated_at``) are always promoted and are handled by the mapper
    unconditionally, so ``_indexed_fields`` should list **only** the
    extra table-specific columns.
    """
    __abstract__ = True
    id: Mapped[str] = mapped_column(String(_ID_LEN), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(), index=True, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    _record_cls: ClassVar[type]
    _indexed_fields: ClassVar[tuple[str, ...]] = ()

    @classmethod
    def get_indexed_fields(cls) -> tuple[str, ...]:
        """Return the tuple of record fields promoted to dedicated columns."""
        return cls._indexed_fields

class CredentialRow(_JsonRecordMixin):
    """One row per :class:`~agentscope.app.storage.CredentialRecord`."""
    __tablename__ = 'credentials'
    user_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    _indexed_fields = ('user_id',)

class AgentRow(_JsonRecordMixin):
    """One row per :class:`~agentscope.app.storage.AgentRecord`."""
    __tablename__ = 'agents'
    user_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    __table_args__ = (Index('ix_agents_user_source', 'user_id', 'source'),)
    _indexed_fields = ('user_id', 'source')

class SessionRow(_JsonRecordMixin):
    """One row per :class:`~agentscope.app.storage.SessionRecord`."""
    __tablename__ = 'sessions'
    user_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    source_schedule_id: Mapped[str | None] = mapped_column(String(_ID_LEN), nullable=True, index=True)
    team_id: Mapped[str | None] = mapped_column(String(_ID_LEN), nullable=True, index=True)
    # ── SKPL: cross-device session bridging ────────────────────────────
    device_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    # ────────────────────────────────────────────────────────────────────
    __table_args__ = (Index('ix_sessions_user_agent', 'user_id', 'agent_id'),)
    _indexed_fields = ('user_id', 'agent_id', 'source', 'source_schedule_id', 'team_id')

class ScheduleRow(_JsonRecordMixin):
    """One row per :class:`~agentscope.app.storage.ScheduleRecord`."""
    __tablename__ = 'schedules'
    user_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    _indexed_fields = ('user_id', 'agent_id')

class TeamRow(_JsonRecordMixin):
    """One row per :class:`~agentscope.app.storage.TeamRecord`."""
    __tablename__ = 'teams'
    user_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False)
    _indexed_fields = ('user_id', 'session_id')

class KnowledgeBaseRow(_JsonRecordMixin):
    """One row per :class:`~agentscope.app.storage.KnowledgeBaseRecord`."""
    __tablename__ = 'knowledge_bases'
    user_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    # ── SKPL: organization-scoped sharing ───────────────────────────────
    org_id: Mapped[str | None] = mapped_column(String(_ID_LEN), nullable=True, index=True)
    visibility: Mapped[str] = mapped_column(
        String(16), nullable=False, default="private",
        doc="'private' | 'org' | 'public'",
    )
    is_public = Column(Integer, default=0)
    # ────────────────────────────────────────────────────────────────────
    _indexed_fields = ('user_id',)

class KnowledgeDocumentRow(_JsonRecordMixin):
    """One row per :class:`KnowledgeDocumentRecord`.

    Promotes every lifecycle / sweeper field to a dedicated column so
    :meth:`AsyncSQLAlchemyStorage.list_knowledge_documents_with_expired_lease`
    can filter without deserialising :attr:`payload`. The composite
    ``(status, lease_expires_at)`` index serves both the expired-lease
    sweep (``WHERE status NOT IN (…) AND lease_expires_at < :now``)
    and the pending-orphan sweep (``WHERE status = 'pending' AND
    created_at < :threshold`` — covered by the plain ``status`` index
    combined with the mixin's ``created_at`` index).
    """
    __tablename__ = 'knowledge_documents'
    user_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    knowledge_base_id: Mapped[str] = mapped_column(String(_ID_LEN), ForeignKey('knowledge_bases.id', ondelete='CASCADE'), nullable=False, index=True)
    processing_node: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    __table_args__ = (Index('ix_kd_status_lease', 'status', 'lease_expires_at'), Index('ix_kd_user_kb', 'user_id', 'knowledge_base_id'))
    _indexed_fields = ('user_id', 'knowledge_base_id', 'processing_node', 'status', 'lease_expires_at')

class MessageRow(_Base):
    """One row per persisted :class:`~agentscope.message.Msg`.

    Sits outside the ``_JsonRecordMixin`` family because messages are
    not stand-alone records — they are per-session events. A message is
    identified by the **composite** primary key ``(session_id, msg_id)``
    rather than a synthetic concatenated string: ``Msg.id`` is only
    unique *within* a session, and a composite key keeps the write path
    ("same ``(session, msg_id)`` → replace", inheriting
    :class:`RedisStorage.upsert_message`'s semantic) enforced by the DB
    without having to bound the length of a ``session_id:msg_id`` blob
    (both ids come from a user-overridable id factory).
    """
    __tablename__ = 'messages'
    session_id: Mapped[str] = mapped_column(String(_ID_LEN), primary_key=True)
    msg_id: Mapped[str] = mapped_column(String(_ID_LEN), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    __table_args__ = (Index('ix_messages_session_created', 'session_id', 'created_at'),)


# ==============================================================================
# SKPL Agent Extension Tables
# ==============================================================================
# These tables are added by SKPL Agent and are NOT present in upstream
# AgentScope. They support the OpenWolf context management, Agent-S
# desktop automation, and multi-tenant quota features.

# ---------------------------------------------------------------------------
# Context Management (OpenWolf)
# ---------------------------------------------------------------------------

class AnatomySymbolRow(_Base):
    """Symbol extracted from source code during anatomy scanning."""
    __tablename__ = 'skpl_anatomy_symbols'

    id: Mapped[str] = mapped_column(String(_ID_LEN), primary_key=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    symbol_name: Mapped[str] = mapped_column(String(256), nullable=False)
    symbol_type: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    line_start: Mapped[int] = mapped_column(nullable=False)
    line_end: Mapped[int] = mapped_column(nullable=False)
    signature: Mapped[str | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(nullable=True)
    parent_symbol: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_exported: Mapped[bool] = mapped_column(default=False)
    token_count: Mapped[int | None] = mapped_column(nullable=True)
    hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_anatomy_file', 'file_path'),
        Index('idx_anatomy_symbol', 'symbol_name'),
        Index('idx_anatomy_lang_type', 'language', 'symbol_type'),
        Index('idx_anatomy_hash', 'hash'),
    )


class BugLogRow(_Base):
    """Record of bugs encountered during agent execution."""
    __tablename__ = 'skpl_buglogs'

    id: Mapped[str] = mapped_column(String(_ID_LEN), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    agent_id: Mapped[str | None] = mapped_column(String(_ID_LEN), nullable=True)
    error_type: Mapped[str] = mapped_column(String(128), nullable=False)
    error_message: Mapped[str] = mapped_column(nullable=False)
    error_traceback: Mapped[str | None] = mapped_column(nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    line_number: Mapped[int | None] = mapped_column(nullable=True)
    context_snippet: Mapped[str | None] = mapped_column(nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    duplicate_of: Mapped[str | None] = mapped_column(String(_ID_LEN), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default='open')
    resolution: Mapped[str | None] = mapped_column(nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_buglog_session', 'session_id'),
        Index('idx_buglog_fingerprint', 'fingerprint'),
        Index('idx_buglog_status', 'status'),
    )


class TokenLedgerRow(_Base):
    """Token usage tracking per session/agent."""
    __tablename__ = 'skpl_token_ledgers'

    id: Mapped[str] = mapped_column(String(_ID_LEN), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    agent_id: Mapped[str | None] = mapped_column(String(_ID_LEN), nullable=True)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    total_tokens: Mapped[int] = mapped_column(default=0)
    token_budget: Mapped[int | None] = mapped_column(nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_waste: Mapped[bool] = mapped_column(default=False)
    waste_reason: Mapped[str | None] = mapped_column(nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_token_session', 'session_id'),
        Index('idx_token_recorded', 'recorded_at'),
        Index('idx_token_waste', 'is_waste'),
    )


class CerebrumRow(_Base):
    """Agent "brain" state persistence."""
    __tablename__ = 'skpl_cerebrum'

    id: Mapped[str] = mapped_column(String(_ID_LEN), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(256), nullable=False)
    value: Mapped[str] = mapped_column(nullable=False)
    category: Mapped[str] = mapped_column(String(64), default='general')
    confidence: Mapped[float] = mapped_column(default=1.0)
    source: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ttl_seconds: Mapped[int | None] = mapped_column(nullable=True)
    access_count: Mapped[int] = mapped_column(default=0)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_cerebrum_agent', 'agent_id'),
        Index('idx_cerebrum_key', 'agent_id', 'key'),
        Index('idx_cerebrum_category', 'agent_id', 'category'),
    )


class SessionContextRow(_Base):
    """Session-level context state for agent sessions."""
    __tablename__ = 'skpl_session_contexts'

    id: Mapped[str] = mapped_column(String(_ID_LEN), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, unique=True, index=True)
    project_root: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    active_file: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    context_json: Mapped[str | None] = mapped_column(nullable=True)
    total_tokens_used: Mapped[int] = mapped_column(default=0)
    token_budget: Mapped[int] = mapped_column(default=200000)
    is_active: Mapped[bool] = mapped_column(default=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Desktop Automation (Agent-S)
# ---------------------------------------------------------------------------

class DesktopNodeRow(_Base):
    """Registered desktop agent node."""
    __tablename__ = 'skpl_desktop_nodes'

    id: Mapped[str] = mapped_column(String(_ID_LEN), primary_key=True)
    node_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    hostname: Mapped[str | None] = mapped_column(String(256), nullable=True)
    capabilities: Mapped[str] = mapped_column(default='[]')
    screen_width: Mapped[int | None] = mapped_column(nullable=True)
    screen_height: Mapped[int | None] = mapped_column(nullable=True)
    version: Mapped[str] = mapped_column(String(32), default='1.0.0')
    status: Mapped[str] = mapped_column(String(32), default='offline')
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actions_this_minute: Mapped[int] = mapped_column(default=0)
    total_actions: Mapped[int] = mapped_column(default=0)
    metadata_json: Mapped[str | None] = mapped_column(nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_desktop_tenant', 'tenant_id'),
        Index('idx_desktop_status', 'status'),
        Index('idx_desktop_heartbeat', 'last_heartbeat'),
    )


class DesktopActionLogRow(_Base):
    """Audit log of desktop automation actions."""
    __tablename__ = 'skpl_desktop_action_logs'

    id: Mapped[str] = mapped_column(String(_ID_LEN), primary_key=True)
    node_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    command_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, unique=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    params_json: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(32), default='pending')
    result_json: Mapped[str | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    grounding_used: Mapped[bool] = mapped_column(default=False)
    grounding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_x: Mapped[int | None] = mapped_column(nullable=True)
    target_y: Mapped[int | None] = mapped_column(nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_desktop_action_node', 'node_id'),
        Index('idx_desktop_action_session', 'session_id'),
        Index('idx_desktop_action_status', 'status'),
        Index('idx_desktop_action_requested', 'requested_at'),
    )


class DesktopSessionRow(_Base):
    """Desktop automation session tracking."""
    __tablename__ = 'skpl_desktop_sessions'

    id: Mapped[str] = mapped_column(String(_ID_LEN), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, unique=True, index=True)
    agent_session_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default='active')
    total_actions: Mapped[int] = mapped_column(default=0)
    successful_actions: Mapped[int] = mapped_column(default=0)
    failed_actions: Mapped[int] = mapped_column(default=0)
    screenshot_count: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_desktop_sess_agent', 'agent_session_id'),
        Index('idx_desktop_sess_node', 'node_id'),
        Index('idx_desktop_sess_status', 'status'),
    )


# ---------------------------------------------------------------------------
# Quota Management
# ---------------------------------------------------------------------------

class TenantQuotaRow(_Base):
    """Per-tenant resource quota configuration."""
    __tablename__ = 'skpl_tenant_quotas'

    id: Mapped[str] = mapped_column(String(_ID_LEN), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, unique=True, index=True)
    max_agents: Mapped[int] = mapped_column(default=10)
    max_sessions: Mapped[int] = mapped_column(default=50)
    max_workspaces: Mapped[int] = mapped_column(default=5)
    max_desktop_nodes: Mapped[int] = mapped_column(default=3)
    max_desktop_actions_per_minute: Mapped[int] = mapped_column(default=60)
    max_web_requests_per_day: Mapped[int] = mapped_column(default=10000)
    max_web_requests_per_minute: Mapped[int] = mapped_column(default=30)
    max_token_budget: Mapped[int] = mapped_column(default=1000000)
    max_tokens_per_request: Mapped[int] = mapped_column(default=100000)
    max_storage_mb: Mapped[int] = mapped_column(default=1024)
    max_file_size_mb: Mapped[int] = mapped_column(default=50)
    max_anatomy_symbols: Mapped[int] = mapped_column(default=100000)
    max_buglog_entries: Mapped[int] = mapped_column(default=10000)
    max_api_requests_per_minute: Mapped[int] = mapped_column(default=100)
    is_active: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ResourceUsageRow(_Base):
    """Current resource usage tracking per tenant."""
    __tablename__ = 'skpl_resource_usage'

    id: Mapped[str] = mapped_column(String(_ID_LEN), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(_ID_LEN), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active_agents: Mapped[int] = mapped_column(default=0)
    active_sessions: Mapped[int] = mapped_column(default=0)
    active_workspaces: Mapped[int] = mapped_column(default=0)
    registered_desktop_nodes: Mapped[int] = mapped_column(default=0)
    web_requests_today: Mapped[int] = mapped_column(default=0)
    tokens_used_today: Mapped[int] = mapped_column(default=0)
    desktop_actions_today: Mapped[int] = mapped_column(default=0)
    api_requests_today: Mapped[int] = mapped_column(default=0)
    storage_used_mb: Mapped[float] = mapped_column(default=0.0)
    anatomy_symbols_count: Mapped[int] = mapped_column(default=0)
    buglog_entries_count: Mapped[int] = mapped_column(default=0)
    last_daily_reset: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_usage_tenant', 'tenant_id'),
    )