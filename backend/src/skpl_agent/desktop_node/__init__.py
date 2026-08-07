"""SKPL Desktop Node — edge node for desktop automation.

This module runs on user machines and connects to the SKPL Agent
control center via WebSocket to receive and execute desktop operations.

Architecture:
    desktop_node/
        ├── config.py      — Node configuration (DesktopNodeConfig)
        ├── events.py      — Message protocol types and serialization
        ├── node_info.py   — System capability collection
        ├── screen.py      — Screen capture (multi-backend)
        ├── security.py    — Security policy and code validation
        ├── executor.py    — Action execution engine
        ├── heartbeat.py   — Heartbeat and connection monitoring
        ├── grounding.py   — UI element grounding (OmniParser)
        ├── ws_client.py   — WebSocket client for control center
        ├── cli.py         — CLI entry point
        └── __main__.py    — Module entry point

Usage:
    python -m skpl_agent.desktop_node --server ws://localhost:8000 --token <jwt>
"""

from skpl_agent.desktop_node.config import DesktopNodeConfig
from skpl_agent.desktop_node.events import (
    MessageType,
    ActionType,
    ActionStatus,
    NodeStatus,
    BaseMessage,
    HelloMessage,
    WelcomeMessage,
    HeartbeatMessage,
    ActionRequest,
    ActionResult,
    ScreenshotRequest,
    ScreenshotResponse,
    GroundingRequest,
    GroundingResponse,
    ErrorMessage,
    serialize_message,
    deserialize_message,
)
from skpl_agent.desktop_node.node_info import NodeInfo, NodeInfoCollector
from skpl_agent.desktop_node.screen import ScreenCapture
from skpl_agent.desktop_node.security import (
    SecurityPolicy,
    SecurityError,
    AppSecurityError,
    CodeSecurityError,
    ResourceLimitError,
)
from skpl_agent.desktop_node.executor import ActionExecutor, DesktopExecutor, RateLimitError
from skpl_agent.desktop_node.heartbeat import HeartbeatManager
from skpl_agent.desktop_node.grounding import (
    GroundingModel,
    GroundingResult,
    OmniParserGrounding,
    SimpleGrounding,
    create_grounding_model,
)
from skpl_agent.desktop_node.ws_client import DesktopNodeWSClient

__version__ = "0.2.0"

__all__ = [
    # Config
    "DesktopNodeConfig",
    # Events
    "MessageType",
    "ActionType",
    "ActionStatus",
    "NodeStatus",
    "BaseMessage",
    "HelloMessage",
    "WelcomeMessage",
    "HeartbeatMessage",
    "ActionRequest",
    "ActionResult",
    "ScreenshotRequest",
    "ScreenshotResponse",
    "GroundingRequest",
    "GroundingResponse",
    "ErrorMessage",
    "serialize_message",
    "deserialize_message",
    # Node Info
    "NodeInfo",
    "NodeInfoCollector",
    # Screen
    "ScreenCapture",
    # Security
    "SecurityPolicy",
    "SecurityError",
    "AppSecurityError",
    "CodeSecurityError",
    "ResourceLimitError",
    # Executor
    "ActionExecutor",
    "DesktopExecutor",
    "RateLimitError",
    # Heartbeat
    "HeartbeatManager",
    # Grounding
    "GroundingModel",
    "GroundingResult",
    "OmniParserGrounding",
    "SimpleGrounding",
    "create_grounding_model",
    # WS Client
    "DesktopNodeWSClient",
]