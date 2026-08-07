"""The lifespan of the agent service."""
import logging
import socket
import uuid
from contextlib import AsyncExitStack, asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncIterator

logger = logging.getLogger(__name__)
from ._manager import BackgroundTaskManager, CancelDispatcher, ChatRunRegistry, ContextManager, FileWatchManager, ScanTaskManager, SchedulerManager, UpdateManager, WakeupDispatcher
from ._service import ChatService, IndexSweeper, IndexTaskConsumer, IndexWorker, KnowledgeBaseService, ResourceAccessService, SessionService, TokenSavingService
from skpl_agent.config import get_settings
from skpl_agent.updates.service import UpdateService
if TYPE_CHECKING:
    from fastapi import FastAPI
else:
    FastAPI = Any

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown of all application-wide resources.

    Every resource with a lifecycle is an async context manager and is
    entered through a single :class:`AsyncExitStack`. The stack tears
    them down in reverse order on shutdown — including when an entry
    later in the sequence raises during startup, so no resource leaks
    on partial failure.

    Service-layer ``ChatService`` and ``SessionService`` have no
    lifecycle of their own and are constructed inline.
    """
    storage = app.state.storage
    message_bus = app.state.message_bus
    workspace_manager = app.state.workspace_manager
    knowledge_base_manager = app.state.knowledge_base_manager
    blob_store = app.state.blob_store
    enable_index_worker = app.state.enable_index_worker
    resource_access_policy = app.state.resource_access_policy
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(storage)
        # ── Ensure admin user exists ─────────────────────────────────
        try:
            auth_service = getattr(app.state, "auth_service", None)
            if auth_service is not None:
                existing = await auth_service.get_user_by_username("admin")
                if existing is None:
                    await auth_service.register(
                        username="admin",
                        password="admin123",
                        role="admin",
                    )
                    logger.info("Created admin user (admin/admin123)")
        except Exception as e:
            logger.warning("Failed to ensure admin user: %s", e)
        await stack.enter_async_context(message_bus)
        await stack.enter_async_context(workspace_manager)
        if knowledge_base_manager is not None:
            await stack.enter_async_context(knowledge_base_manager)
        if blob_store is not None:
            await stack.enter_async_context(blob_store)
        bg_manager = await stack.enter_async_context(BackgroundTaskManager(message_bus=message_bus))
        app.state.background_task_manager = bg_manager
        chat_run_registry = await stack.enter_async_context(ChatRunRegistry())
        app.state.chat_run_registry = chat_run_registry
        scheduler = await stack.enter_async_context(SchedulerManager(storage=storage, message_bus=message_bus))
        app.state.scheduler_manager = scheduler
        resource_access_service = ResourceAccessService(storage=storage, policy=resource_access_policy)
        app.state.resource_access_service = resource_access_service
        chat_service = ChatService(storage=storage, workspace_manager=workspace_manager, scheduler_manager=scheduler, background_task_manager=bg_manager, message_bus=message_bus, resource_access_service=resource_access_service, knowledge_base_manager=knowledge_base_manager, extra_agent_middlewares=app.state.extra_agent_middlewares, extra_agent_tools=app.state.extra_agent_tools, custom_subagent_templates=app.state.custom_subagent_templates, custom_agent_cls=app.state.custom_agent_cls)
        app.state.chat_service = chat_service
        app.state.session_service = SessionService(storage=storage, message_bus=message_bus)
        knowledge_base_service = None
        if knowledge_base_manager is not None:
            if enable_index_worker:
                node_id = f'{socket.gethostname()}:{uuid.uuid4().hex[:8]}'
                worker = IndexWorker(storage=storage, blob_store=blob_store, knowledge_base_manager=knowledge_base_manager, parsers=app.state.knowledge_parsers, chunker=app.state.knowledge_chunker, node_id=node_id)
                await stack.enter_async_context(IndexTaskConsumer(message_bus=message_bus, worker=worker))
            sweeper = IndexSweeper(storage=storage, message_bus=message_bus)
            await sweeper.start()
            stack.push_async_callback(sweeper.stop)
            knowledge_base_service = KnowledgeBaseService(storage=storage, knowledge_base_manager=knowledge_base_manager, blob_store=blob_store, message_bus=message_bus, resource_access_service=resource_access_service)
        app.state.knowledge_base_service = knowledge_base_service
        # ── Connect KB service to MemoryManager ────────────────────────
        memory_manager = getattr(app.state, "memory_manager", None)
        if memory_manager is not None and knowledge_base_service is not None:
            memory_manager.connect_kb_service(knowledge_base_service)
        # ── Mem0 L2: retry initialization during lifespan ──────────────
        if memory_manager is not None and not memory_manager.health()["l2_mem0"]:
            try:
                from skpl_agent.app._mem0_utils import init_mem0_for_manager
                init_mem0_for_manager(memory_manager, get_settings())
            except Exception as e:
                logger.warning("Mem0 lifespan initialization failed: %s", e)
        # ── SKPL Context Managers ────────────────────────────────────
        context_manager = ContextManager()
        app.state.context_manager = context_manager
        scan_task_manager = ScanTaskManager()
        await scan_task_manager.start()
        stack.push_async_callback(scan_task_manager.stop)
        app.state.scan_task_manager = scan_task_manager
        file_watch_manager = FileWatchManager(
            watch_path=".",
            on_change=lambda files: logger.info("Files changed: %s", files),
        )
        app.state.file_watch_manager = file_watch_manager
        await stack.enter_async_context(WakeupDispatcher(message_bus=message_bus, storage=storage, chat_service=chat_service, chat_run_registry=chat_run_registry))
        await stack.enter_async_context(CancelDispatcher(message_bus=message_bus, registry=chat_run_registry, bg_manager=bg_manager))
        # ── SKPL Update Service ─────────────────────────────────────────
        cfg = get_settings()
        update_service = UpdateService(
            check_interval_hours=cfg.update.check_interval_hours,
            auto_merge=cfg.update.notify_on_update,
            notify_on_update=cfg.update.notify_on_update,
            webhook_url=cfg.update.webhook_url or "",
        )
        await update_service.start()
        app.state.update_service = update_service
        stack.push_async_callback(update_service.stop)
        update_manager = UpdateManager(
            check_interval_hours=cfg.update.check_interval_hours,
        )
        update_manager.start()
        app.state.update_manager = update_manager
        async def _stop_update():
            update_manager.stop()
        stack.push_async_callback(_stop_update)
        # ── SKPL Token Saving Service ───────────────────────────────────
        token_saving_service = TokenSavingService()
        app.state.token_saving_service = token_saving_service

        # ── SKPL Memory Enhancer (APScheduler) ──────────────────────────
        try:
            from skpl_agent.app._memory._memory_enhancer import (
                setup_memory_enhancer_scheduler,
                shutdown_memory_enhancer_scheduler,
            )
            setup_memory_enhancer_scheduler(app, interval_minutes=30)
            async def _stop_memory_enhancer():
                shutdown_memory_enhancer_scheduler(app)
            stack.push_async_callback(_stop_memory_enhancer)
            logger.info("MemoryEnhancer scheduler started")
        except Exception as e:
            logger.warning("MemoryEnhancer scheduler setup failed: %s", e)

        yield