"""The storage module in skpl_agent."""
from typing import TYPE_CHECKING
from ._base import StorageBase
from ._redis_storage import RedisStorage
from ._model import AgentData, AgentRecord, CredentialRecord, KnowledgeBaseData, KnowledgeBaseRecord, KnowledgeDocumentData, KnowledgeDocumentRecord, KnowledgeDocumentStatus, ScheduleData, ScheduleRecord, ScheduleSource, SessionConfig, SessionKnowledgeConfig, SessionRecord, SessionSource, ChatModelConfig, TTSModelConfig, EmbeddingModelConfig, TeamData, TeamRecord, UserRecord, TeamMember, InviteConfig
if TYPE_CHECKING:
    from ._sql import AsyncSQLAlchemyStorage

def __getattr__(name: str) -> object:
    """Lazily load the optional SQL backend on first attribute access.

    Keeps ``import agentscope.app.storage`` cheap — ``StorageBase``,
    ``RedisStorage`` and the record models never need SQLAlchemy — while
    still exposing ``AsyncSQLAlchemyStorage`` from this package for
    callers that do ``from agentscope.app.storage import
    AsyncSQLAlchemyStorage``. SQLAlchemy is imported only at that point.
    """
    if name == 'AsyncSQLAlchemyStorage':
        from ._sql import AsyncSQLAlchemyStorage as _AsyncSQLAlchemyStorage
        return _AsyncSQLAlchemyStorage
    raise AttributeError(f"module 'skpl_agent.app.storage' has no attribute {name!r}")
__all__ = ['StorageBase', 'RedisStorage', 'AsyncSQLAlchemyStorage', 'InviteConfig', 'AgentData', 'AgentRecord', 'CredentialRecord', 'KnowledgeBaseData', 'KnowledgeBaseRecord', 'KnowledgeDocumentData', 'KnowledgeDocumentRecord', 'KnowledgeDocumentStatus', 'SessionConfig', 'SessionKnowledgeConfig', 'SessionRecord', 'SessionSource', 'ChatModelConfig', 'TTSModelConfig', 'EmbeddingModelConfig', 'TeamMember', 'TeamData', 'TeamRecord', 'UserRecord', 'ScheduleData', 'ScheduleRecord', 'ScheduleSource']