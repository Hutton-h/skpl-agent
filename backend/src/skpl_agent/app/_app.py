"""SKPL Agent app factory."""
import os
from pathlib import Path
from typing import Type, TYPE_CHECKING, Any
from ._lifespan import lifespan
from .access import DenyAllResourceAccessPolicy, ResourceAccessPolicyBase
from .rag.blob_store import BlobStoreBase, LocalBlobStore
from .rag.knowledge_base_manager import KnowledgeBaseManagerBase
from .workspace_manager import WorkspaceManagerBase, LocalWorkspaceManager
from ._router import agent_router, chat_router, code_generation_router, context_router, credential_router, desktop_automation_router, desktop_node_router, file_router, firecrawl_router, knowledge_base_router, model_router, tts_model_router, quota_router, schedule_router, session_router, template_router, update_router, web_intelligence_router, workspace_router, create_shield_router
from ._types import AgentMiddlewareFactory, AgentToolFactory, SubAgentTemplate
from .message_bus import MessageBus, InMemoryMessageBus
from .storage import StorageBase
from ._middleware import GroundingMiddleware, QuotaMiddleware
from ..agent import Agent
from ..credential import CredentialFactory, CredentialBase
from ..rag import ApproxTokenChunker, ChunkerBase, ParserBase, TextParser
from .._version import __version__
if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi.middleware import Middleware as FastAPIMiddleware
else:
    FastAPI = Any
    FastAPIMiddleware = Any

def create_app(storage: StorageBase, message_bus: MessageBus, workspace_manager: WorkspaceManagerBase, knowledge_base_manager: KnowledgeBaseManagerBase | None=None, knowledge_parsers: list[ParserBase] | dict[str, ParserBase] | None=None, knowledge_chunker: ChunkerBase | None=None, blob_store: BlobStoreBase | None=None, enable_index_worker: bool=True, *, extra_credentials: list[Type[CredentialBase]] | None=None, extra_middlewares: list[FastAPIMiddleware] | None=None, extra_agent_middlewares: AgentMiddlewareFactory | None=None, extra_agent_tools: AgentToolFactory | None=None, custom_subagent_templates: list[SubAgentTemplate] | None=None, custom_agent_cls: Type[Agent] | None=None, resource_access_policy: ResourceAccessPolicyBase | None=None, title: str='SKPL Agent', version: str=__version__) -> FastAPI:
    """Create and configure a FastAPI application.

    This is the primary entry point for embedding AgentScope into an existing
    service or running it standalone.  All built-in routers are registered
    automatically; pass ``extra_middlewares`` to add your own.

    Usage — standalone::

        app = create_app(
            storage=RedisStorage(),
            message_bus=RedisMessageBus(),
            workspace_manager=LocalWorkspaceManager(),
        )
        uvicorn.run(app, host="0.0.0.0", port=8000)

    Usage — mount onto an existing app::

        root = FastAPI()
        agentscope_app = create_app(
            storage=RedisStorage(),
            message_bus=RedisMessageBus(),
            workspace_manager=LocalWorkspaceManager(),
        )
        root.mount("/agentscope", agentscope_app)

    Args:
        storage (`StorageBase`):
            The storage backend.  Its lifecycle (``__aenter__`` /
            ``__aexit__``) is managed by the app lifespan.
        message_bus (`MessageBus`):
            The live message bus used for cross-session inbox delivery
            and idle-session triggers. Required — the bus is intentionally
            decoupled from ``storage`` so the persistence backend (e.g.
            SQL) can differ from the transport backend (Redis). Its
            lifecycle is also managed by the app lifespan.
        workspace_manager (`WorkspaceManagerBase`):
            The workspace manager. Required — every chat run and every
            ``/workspace`` endpoint depends on it. Its lifecycle (
            ``__aenter__`` / ``__aexit__``) is managed by the app
            lifespan. Pass a :class:`~agentscope.app._manager.
            LocalWorkspaceManager` for local-directory workspaces.
        knowledge_base_manager (`KnowledgeBaseManagerBase | None`,          optional):
            The knowledge base manager that owns knowledge base
            lifecycle and serves
            :class:`~agentscope.rag.KnowledgeBase`
            runtime handles to both HTTP service and agent code.
            The manager carries its own vector store instance — its
            ``__aenter__`` / ``__aexit__`` enter and release that
            vector store, so the caller does not pass the vector
            store separately.  ``None`` disables knowledge base
            endpoints entirely.
        knowledge_parsers (`list[ParserBase] | dict[str, ParserBase] |          None`, optional):
            Parsers registered for knowledge base document uploads.
            Pass a **list** to have the service route by each parser's
            ``supported_media_types`` (later entries override earlier
            ones for overlapping types, with a warning); pass a
            **dict** ``media_type → parser`` for explicit routing
            (one parser bound to multiple types, type aliases, ...).
            Defaults to ``[TextParser()]`` when
            ``knowledge_base_manager`` is set.
        knowledge_chunker (`ChunkerBase | None`, optional):
            The chunker shared across every knowledge base.  Defaults
            to :class:`~agentscope.rag.ApproxTokenChunker()` when
            ``knowledge_base_manager`` is set.
        blob_store (`BlobStoreBase | None`, optional):
            Backend storing uploaded document bytes between the
            upload endpoint and the indexing worker.  Required when
            ``knowledge_base_manager`` is set; defaults to
            :class:`~agentscope.app.rag.blob_store.LocalBlobStore`
            rooted at ``./blobs``.  Its lifecycle (``__aenter__`` /
            ``__aexit__``) is managed by the app lifespan.
        enable_index_worker (`bool`, defaults to ``True``):
            When ``True`` (embedded deployment) the API process starts
            an :class:`~agentscope.app._service.IndexWorker` and an
            :class:`~agentscope.app._service.IndexSweeper` in its
            lifespan, and dispatches indexing tasks via an
            in-process queue.  When ``False`` (dedicated deployment)
            the API process performs no indexing — a separate worker
            process is expected to consume tasks from the message
            bus.  No effect when ``knowledge_base_manager`` is
            ``None``.
        extra_credentials (`list[Type[CredentialBase]] | None`, optional):
            Additional :class:`~agentscope.credential.CredentialBase`
            subclasses to register before the app starts.  Equivalent to
            calling :func:`~agentscope.credential.CredentialFactory.
            register_credential` for each class.
        extra_middlewares (`list[Middleware] | None`, optional):
            Additional ASGI middlewares to add to the application.
        extra_agent_middlewares (`AgentMiddlewareFactory | None`, optional):
            An async factory ``(user_id, agent_id, session_id) -> awaitable
            of list[MiddlewareBase]`` that produces extra
            :class:`~agentscope.middleware.MiddlewareBase` instances to
            attach to the agent on each invocation.  Called once per agent
            assembly (i.e. per chat turn / scheduled trigger), so it can
            return user/session-specific middleware (auth, audit logging,
            tenant isolation, etc.).  The returned middlewares are appended
            to the framework-supplied ones (e.g. ``ToolOffloadMiddleware``).
        extra_agent_tools (`AgentToolFactory | None`, optional):
            An async factory ``(user_id, agent_id, session_id) -> awaitable
            of list[ToolBase]`` that produces extra
            :class:`~agentscope.tool.ToolBase` instances to register in the
            agent's toolkit on each invocation.  Useful when tool
            availability depends on the caller (per-tenant integrations,
            user-specific credentials).  The returned tools are added to
            the workspace-derived tools in the toolkit's ``"basic"`` group.
        custom_subagent_templates (`list[SubAgentTemplate] | None`, optional):
            Reusable blueprints for sub-agent creation within teams.
            Each template defines a sub-agent *type* (e.g. ``"researcher"``,
            ``"coder"``) with pre-configured system prompt, context config,
            ReAct config, permission context, and task context. When
            registered, the ``AgentCreate`` tool exposes a
            ``subagent_type`` parameter so the leader agent can route to
            the appropriate template.  See
            :class:`~agentscope.app._types.SubAgentTemplate` for details.
        custom_agent_cls (`Type[Agent] | None`, optional):
            A custom :class:`~agentscope.agent.Agent` subclass to use
            when assembling agents.  When ``None`` (default), the
            built-in :class:`~agentscope.agent.Agent` is used.
        resource_access_policy (`ResourceAccessPolicyBase | None`, optional):
            Policy deciding whether a viewer may access
            credentials / agents / knowledge bases owned by another
            user. When ``None`` (default), a
            :class:`DenyAllResourceAccessPolicy` is installed which
            preserves the historical owner-isolated behavior.
        title (`str`, defaults to ``"AgentScope"``):
            OpenAPI title shown in the docs UI.
        version (`str`, defaults to the package version):
            API version shown in the docs UI.

    Returns:
        `FastAPI`: A fully configured application ready to serve requests.
    """
    from fastapi import FastAPI
    for cls in extra_credentials or []:
        CredentialFactory.register_credential(cls)
    app = FastAPI(title=title, version=version, lifespan=lifespan)
    app.state.storage = storage
    app.state.message_bus = message_bus
    app.state.workspace_manager = workspace_manager
    app.state.knowledge_base_manager = knowledge_base_manager
    app.state.extra_agent_middlewares = extra_agent_middlewares
    app.state.extra_agent_tools = extra_agent_tools
    app.state.custom_agent_cls = custom_agent_cls
    app.state.resource_access_policy = resource_access_policy or DenyAllResourceAccessPolicy()
    if knowledge_base_manager is not None:
        app.state.knowledge_parsers = knowledge_parsers if knowledge_parsers is not None else [TextParser()]
        app.state.knowledge_chunker = knowledge_chunker or ApproxTokenChunker()
        app.state.blob_store = blob_store if blob_store is not None else LocalBlobStore(root_dir='./blobs')
    else:
        app.state.knowledge_parsers = knowledge_parsers
        app.state.knowledge_chunker = knowledge_chunker
        app.state.blob_store = blob_store
    app.state.enable_index_worker = enable_index_worker and knowledge_base_manager is not None
    templates = custom_subagent_templates or []
    seen_types: set[str] = set()
    duplicates: set[str] = set()
    for t in templates:
        if t.type in seen_types:
            duplicates.add(t.type)
        seen_types.add(t.type)
    if duplicates:
        raise ValueError(f'Duplicate sub_agent_template type(s): {duplicates}')
    app.state.custom_subagent_templates = {t.type: t for t in templates}
    for router in (agent_router, chat_router, code_generation_router, context_router, credential_router, desktop_automation_router, desktop_node_router, file_router, firecrawl_router, knowledge_base_router, quota_router, schedule_router, session_router, template_router, update_router, web_intelligence_router, workspace_router, model_router, tts_model_router, create_shield_router()):
        app.include_router(router)
    # ── SKPL: register auth router ───────────────────────────────────────
    try:
        from skpl_agent.app._auth.router import router as auth_router
        app.include_router(auth_router)
    except ImportError:
        pass
    # ── SKPL: register organization router ─────────────────────────────
    try:
        from skpl_agent.app._organization.router import router as org_router
        app.include_router(org_router)
    except ImportError:
        pass
    # ── SKPL: register memory router ──────────────────────────────────
    try:
        from skpl_agent.app._memory.router import router as memory_router
        app.include_router(memory_router)
    except ImportError:
        pass
    # ──────────────────────────────────────────────────────────────────────
    # ── SKPL: register admin router ──────────────────────────────────
    try:
        from skpl_agent.app._router._admin import router as admin_router
        app.include_router(admin_router)
    except ImportError:
        pass

    # -- SKPL: register notification router --------------------------
    try:
        from skpl_agent.app._router._notification import router as notification_router
        app.include_router(notification_router)
    except ImportError:
        pass

    # -- SKPL: register skill library router --------------------------
    try:
        from skpl_agent.app._router._skill_library import router as skill_library_router
        app.include_router(skill_library_router)
    except ImportError:
        pass

    for middleware in extra_middlewares or []:
        app.add_middleware(middleware.cls, **middleware.kwargs)
    app.add_middleware(GroundingMiddleware)
    app.add_middleware(QuotaMiddleware)
    return app


# ---------------------------------------------------------------------------
# Development default app — used by `uvicorn skpl_agent.app._app:app`
# ---------------------------------------------------------------------------

def _create_dev_app() -> FastAPI:
    """Create a development app with sensible defaults (SQLite + in-memory bus)."""
    from fastapi.middleware.cors import CORSMiddleware
    from .storage import AsyncSQLAlchemyStorage
    from ..rag._vdb._milvus_lite import MilvusLiteStore
    from .rag.knowledge_base_manager._collection_per_kb import CollectionPerKbManager

    # Use SKPL_DATA_DIR env var if set (Docker/production), otherwise auto-detect
    data_dir = os.environ.get("SKPL_DATA_DIR")
    if not data_dir:
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "data",
        )
    try:
        os.makedirs(data_dir, exist_ok=True)
    except (PermissionError, OSError):
        # Fallback to a writable location when running as non-root
        import tempfile
        data_dir = os.path.join(tempfile.gettempdir(), "skpl-data")
        try:
            os.makedirs(data_dir, exist_ok=True)
        except (PermissionError, OSError):
            # Last resort: use a temp dir that we know exists
            data_dir = tempfile.mkdtemp(prefix="skpl-")

    # Project root: use SKPL_PROJECT_ROOT env var or auto-detect
    project_root = os.environ.get("SKPL_PROJECT_ROOT") or str(Path(__file__).resolve().parents[4])
    skills_dir = os.path.join(project_root, "skills")
    try:
        skill_paths = [
            os.path.join(skills_dir, d)
            for d in os.listdir(skills_dir)
            if os.path.isdir(os.path.join(skills_dir, d))
            and os.path.isfile(os.path.join(skills_dir, d, "SKILL.md"))
        ] if os.path.isdir(skills_dir) else []
    except (PermissionError, FileNotFoundError, OSError):
        skill_paths = []

    storage = AsyncSQLAlchemyStorage(
        f"sqlite+aiosqlite:///{data_dir}/skpl.db",
        create_tables=True,
    )
    message_bus = InMemoryMessageBus()
    workspace_manager = LocalWorkspaceManager(
        basedir=os.path.join(data_dir, "workspaces"),
        skill_paths=skill_paths,
    )
    # Knowledge base: local Milvus Lite vector store
    vector_store = MilvusLiteStore(
        uri=os.path.join(data_dir, "milvus_lite.db"),
    )
    knowledge_base_manager = CollectionPerKbManager(
        storage=storage,
        vector_store=vector_store,
    )

    app = create_app(
        storage=storage,
        message_bus=message_bus,
        workspace_manager=workspace_manager,
        knowledge_base_manager=knowledge_base_manager,
        title="SKPL Agent",
        version=__version__,
    )

    # Add CORS middleware for dev frontend (ports 5173-5180)
    from skpl_agent.config import get_settings
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.core.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── SKPL: Auth system setup ─────────────────────────────────────────
    _setup_auth(app, settings, storage)
    # ─────────────────────────────────────────────────────────────────────

    # ── Rules + Skill Routing Middleware: inject behavioral constraints ──
    # Always inject RulesMiddleware for every agent. SkillRoutingMiddleware
    # is added when skills are available in the workspace.
    from skpl_agent.app._middleware.rules_middleware import (
        RulesMiddleware,
        SkillRoutingMiddleware,
    )

    _prev_middleware_factory = None

    # ── Mem0 Agent Middleware: inject L2 memory into every agent ────────
    _memory_manager = getattr(app.state, "memory_manager", None)
    if _memory_manager is not None and _memory_manager._mem0 is not None:
        from skpl_agent.middleware._longterm_memory._mem0._middleware import Mem0Middleware

        async def _mem0_factory(user_id: str, agent_id: str, session_id: str):
            """Create Mem0 middleware for agent L2 memory awareness."""
            mm = app.state.memory_manager
            if mm is None or mm._mem0 is None:
                return []
            return [Mem0Middleware(
                user_id=user_id,
                client=mm._mem0,
                agent_id=agent_id,
                mode="both",
            )]

        _prev_middleware_factory = _mem0_factory

    async def _rules_middleware_factory(user_id: str, agent_id: str, session_id: str):
        """Create Rules + Skill Routing middleware for every agent, chained with Mem0."""
        middlewares = []
        # 1. Always add behavioral rules
        middlewares.append(RulesMiddleware(
            coding=True,
            security=True,
            communication=True,
            tools=True,
        ))
        # 2. Add skill routing if workspace has skills
        try:
            ws = await workspace_manager.get_workspace(user_id, agent_id, session_id)
            skills = await ws.list_skills()
            if skills:
                skill_dicts = [
                    {
                        "name": s.name,
                        "description": getattr(s, "description", ""),
                        "when_to_use": getattr(s, "when_to_use", ""),
                        "category": getattr(s, "category", ""),
                    }
                    for s in skills
                ]
                middlewares.append(SkillRoutingMiddleware(skill_dicts))
        except Exception:
            pass  # Workspace not available yet — skip skill routing

        # 3. Chain with Mem0 middleware factory
        if _prev_middleware_factory is not None:
            prev = await _prev_middleware_factory(user_id, agent_id, session_id)
            middlewares.extend(prev)
        return middlewares

    app.state.extra_agent_middlewares = _rules_middleware_factory
    _logger = __import__("logging").getLogger(__name__)
    _logger.info("Rules + Skill Routing + Mem0 middleware registered for all agents")

    # ── Desktop Node: WebSocket endpoint for desktop agent connections ──
    _setup_desktop_ws(app, settings)

    # ── Voyage AI compatibility: strip encoding_format from all OpenAI-compatible calls ──
    from ._mem0_utils import _patch_openai_embeddings_for_voyage
    _patch_openai_embeddings_for_voyage(__import__("logging").getLogger(__name__))

    return app


def _setup_auth(app: FastAPI, settings, storage) -> None:
    """Set up JWT, auth, organization, and memory services on the app state.

    This is called during dev app creation to wire up:
    - JWTService (token creation/verification)
    - JWTBearer (FastAPI dependency)
    - AuthService (registration/login)
    - OrgService (organization CRUD)
    - MemoryManager (L1-L4 memory orchestration)

    The services are attached to ``app.state`` so routes can access
    them via dependency injection.
    """
    try:
        from skpl_agent.app._security.jwt_auth import JWTService, JWTBearer
        from skpl_agent.app._auth.service import AuthService
        from skpl_agent.app._auth.models import UserRow  # noqa: F401
        from skpl_agent.app._organization.service import OrgService
        from skpl_agent.app._organization.models import OrganizationRow, OrgMemberRow  # noqa: F401
        from skpl_agent.app._memory.manager import MemoryManager
        from skpl_agent.app._service.cerebrum_service import CerebrumService

        jwt_service = JWTService(
            secret=settings.auth.jwt_secret,
            algorithm=settings.auth.jwt_algorithm,
            default_expiry_hours=settings.auth.jwt_expiry_hours,
        )
        jwt_bearer = JWTBearer(jwt_service)
        auth_service = AuthService(storage, jwt_service)
        org_service = OrgService(storage)
        cerebrum_service = CerebrumService()
        memory_manager = MemoryManager(storage, cerebrum_service=cerebrum_service)

        app.state.jwt_service = jwt_service
        app.state.jwt_bearer = jwt_bearer
        app.state.auth_service = auth_service
        app.state.org_service = org_service
        app.state.memory_manager = memory_manager

        # ── Mem0 L2 Memory: try to initialize early ────────────────────
        init_mem0_for_manager(memory_manager, settings)

        logger = __import__("logging").getLogger(__name__)
        logger.info(
            "Auth system initialized: mode=%s, algorithm=%s, memory=%s",
            settings.auth.mode,
            settings.auth.jwt_algorithm,
            memory_manager.health(),
        )
    except ImportError as e:
        logger = __import__("logging").getLogger(__name__)
        logger.warning("Auth/Org/Memory system not available: %s", e)
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.error("Auth/Org/Memory system setup failed: %s", e)


def _setup_desktop_ws(app, settings):
    """Register desktop node WebSocket and installer download API."""
    from skpl_agent.app._desktop_ws import setup_desktop_ws
    setup_desktop_ws(app, settings)


# Mem0 utilities moved to _mem0_utils.py to break circular import with _lifespan.py
from ._mem0_utils import init_mem0_for_manager


def _create_prod_app() -> FastAPI:
    """Create a production app using environment variables for PostgreSQL + Redis.

    Reads SKPL_CORE_DATABASE_URL and SKPL_CORE_REDIS_URL from environment.
    Falls back to SQLite + InMemoryMessageBus if not configured.
    """
    from fastapi.middleware.cors import CORSMiddleware
    from .storage import AsyncSQLAlchemyStorage
    from ..rag._vdb._milvus_lite import MilvusLiteStore
    from .rag.knowledge_base_manager._collection_per_kb import CollectionPerKbManager
    from skpl_agent.config import get_settings

    settings = get_settings()

    # Determine data directory
    data_dir = os.environ.get("SKPL_DATA_DIR")
    if not data_dir:
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "data",
        )
    try:
        os.makedirs(data_dir, exist_ok=True)
    except (PermissionError, OSError):
        import tempfile
        data_dir = os.path.join(tempfile.gettempdir(), "skpl-data")
        try:
            os.makedirs(data_dir, exist_ok=True)
        except (PermissionError, OSError):
            data_dir = tempfile.mkdtemp(prefix="skpl-")

    # Database: use env var if set, otherwise fall back to SQLite
    database_url = os.environ.get("SKPL_CORE_DATABASE_URL")
    if not database_url:
        database_url = f"sqlite+aiosqlite:///{data_dir}/skpl.db"
        logger = __import__("logging").getLogger(__name__)
        logger.info("SKPL_CORE_DATABASE_URL not set, using SQLite: %s", database_url)
    else:
        logger = __import__("logging").getLogger(__name__)
        logger.info("Using database: %s", database_url.split("@")[-1] if "@" in database_url else database_url)

    storage = AsyncSQLAlchemyStorage(
        database_url,
        create_tables=True,
    )

    # Message bus: use Redis if URL is set, otherwise fall back to in-memory
    redis_url = os.environ.get("SKPL_CORE_REDIS_URL")
    if redis_url:
        try:
            from .message_bus import RedisMessageBus
            message_bus = RedisMessageBus(redis_url)
            logger = __import__("logging").getLogger(__name__)
            logger.info("Using Redis message bus: %s", redis_url.split("@")[-1] if "@" in redis_url else redis_url)
        except ImportError:
            logger = __import__("logging").getLogger(__name__)
            logger.warning("Redis client not installed, falling back to InMemoryMessageBus")
            message_bus = InMemoryMessageBus()
        except Exception as e:
            logger = __import__("logging").getLogger(__name__)
            logger.warning("Failed to connect to Redis (%s), falling back to InMemoryMessageBus", e)
            message_bus = InMemoryMessageBus()
    else:
        message_bus = InMemoryMessageBus()

    # Project root and skills
    project_root = os.environ.get("SKPL_PROJECT_ROOT") or str(Path(__file__).resolve().parents[4])
    skills_dir = os.path.join(project_root, "skills")
    try:
        skill_paths = [
            os.path.join(skills_dir, d)
            for d in os.listdir(skills_dir)
            if os.path.isdir(os.path.join(skills_dir, d))
            and os.path.isfile(os.path.join(skills_dir, d, "SKILL.md"))
        ] if os.path.isdir(skills_dir) else []
    except (PermissionError, FileNotFoundError, OSError):
        skill_paths = []

    workspace_manager = LocalWorkspaceManager(
        basedir=os.path.join(data_dir, "workspaces"),
        skill_paths=skill_paths,
    )

    # Knowledge base: local Milvus Lite
    vector_store = MilvusLiteStore(
        uri=os.path.join(data_dir, "milvus_lite.db"),
    )
    knowledge_base_manager = CollectionPerKbManager(
        storage=storage,
        vector_store=vector_store,
    )

    app = create_app(
        storage=storage,
        message_bus=message_bus,
        workspace_manager=workspace_manager,
        knowledge_base_manager=knowledge_base_manager,
        title="SKPL Agent",
        version=__version__,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.core.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Auth
    _setup_auth(app, settings, storage)

    # Rules + Skill Routing + Mem0 middleware
    from skpl_agent.app._middleware.rules_middleware import (
        RulesMiddleware,
        SkillRoutingMiddleware,
    )
    _prev_middleware_factory = None

    _memory_manager = getattr(app.state, "memory_manager", None)
    if _memory_manager is not None and _memory_manager._mem0 is not None:
        from skpl_agent.middleware._longterm_memory._mem0._middleware import Mem0Middleware

        async def _mem0_factory(user_id: str, agent_id: str, session_id: str):
            mm = app.state.memory_manager
            if mm is None or mm._mem0 is None:
                return []
            return [Mem0Middleware(
                user_id=user_id,
                client=mm._mem0,
                agent_id=agent_id,
                mode="both",
            )]
        _prev_middleware_factory = _mem0_factory

    async def _rules_middleware_factory(user_id: str, agent_id: str, session_id: str):
        middlewares = []
        middlewares.append(RulesMiddleware(
            coding=True,
            security=True,
            communication=True,
            tools=True,
        ))
        try:
            ws = await workspace_manager.get_workspace(user_id, agent_id, session_id)
            skills = await ws.list_skills()
            if skills:
                skill_dicts = [
                    {
                        "name": s.name,
                        "description": getattr(s, "description", ""),
                        "when_to_use": getattr(s, "when_to_use", ""),
                        "category": getattr(s, "category", ""),
                    }
                    for s in skills
                ]
                middlewares.append(SkillRoutingMiddleware(skill_dicts))
        except Exception:
            pass
        if _prev_middleware_factory is not None:
            prev = await _prev_middleware_factory(user_id, agent_id, session_id)
            middlewares.extend(prev)
        return middlewares

    app.state.extra_agent_middlewares = _rules_middleware_factory
    _logger = __import__("logging").getLogger(__name__)
    _logger.info("Rules + Skill Routing + Mem0 middleware registered for all agents")

    # Desktop Node WebSocket
    _setup_desktop_ws(app, settings)

    # Voyage AI compatibility
    from ._mem0_utils import _patch_openai_embeddings_for_voyage
    _patch_openai_embeddings_for_voyage(__import__("logging").getLogger(__name__))

    return app


# Module-level app instance for uvicorn
# Use production mode if DATABASE_URL or REDIS_URL is set, otherwise dev mode
_db_url = os.environ.get("SKPL_CORE_DATABASE_URL", "")
_redis_url = os.environ.get("SKPL_CORE_REDIS_URL", "")
if _db_url.startswith("postgresql") or _redis_url:
    app = _create_prod_app()
else:
    app = _create_dev_app()
