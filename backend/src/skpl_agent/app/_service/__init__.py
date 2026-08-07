"""Service layer modules."""
from ._access import AgentView, CredentialView, KnowledgeBaseView, ResourceAccessService
from ._chat import ChatService
from ._index_sweeper import IndexSweeper
from ._index_task_consumer import IndexTaskConsumer
from ._index_worker import IndexWorker
from ._knowledge_base import KnowledgeBaseService
from ._projectors._subagent_hitl import SubagentHitlProjector
from ._session import SessionService, SessionStatus
from ._session_projection import SessionProjection
from .node_registry import NodeRegistry, RegisteredNode
from .token_saving_service import TokenSavingService

# Shared singleton — instantiated once at app startup
_node_registry: NodeRegistry | None = None


def get_node_registry() -> NodeRegistry:
    """Get or create the shared NodeRegistry singleton."""
    global _node_registry
    if _node_registry is None:
        _node_registry = NodeRegistry()
    return _node_registry