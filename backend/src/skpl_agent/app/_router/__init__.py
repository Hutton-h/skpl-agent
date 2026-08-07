"""App routers."""
from ._agent import agent_router
from ._agent_template import template_router
from ._chat import chat_router
from ._credential import credential_router
from ._file import router as file_router
from ._knowledge_base import knowledge_base_router
from ._schedule import schedule_router
from ._session import session_router
from ._model import model_router
from ._tts_model import tts_model_router
from ._workspace import workspace_router
from .context_router import context_router
from .desktop_automation_router import desktop_automation_router
from .desktop_node_router import desktop_node_router
from .web_intelligence_router import web_intelligence_router
from .code_generation_router import code_generation_router
from .firecrawl_router import router as firecrawl_router
from .quota_router import router as quota_router
from .update_router import update_router
from .._security.agent_shield import create_shield_router

__all__ = [
    "agent_router",
    "template_router",
    "model_router",
    "tts_model_router",
    "chat_router",
    "credential_router",
    "code_generation_router",
    "context_router",
    "desktop_automation_router",
    "desktop_node_router",
    "file_router",
    "firecrawl_router",
    "knowledge_base_router",
    "quota_router",
    "schedule_router",
    "session_router",
    "update_router",
    "web_intelligence_router",
    "workspace_router",
    "create_shield_router",
]
