"""Desktop Node event types — message protocol between node and control center.

All messages use JSON format with a ``type`` field for routing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ── Message Types ────────────────────────────────────────────────────────

class MessageType(str, Enum):
    """Message types for the desktop node protocol."""

    # Connection lifecycle
    HELLO = "hello"                  # Node → Server: initial handshake
    WELCOME = "welcome"              # Server → Node: handshake response
    GOODBYE = "goodbye"              # Node → Server: graceful disconnect

    # Heartbeat
    HEARTBEAT = "heartbeat"          # Node → Server: periodic heartbeat
    HEARTBEAT_ACK = "heartbeat_ack"  # Server → Node: heartbeat acknowledgment

    # Node info
    NODE_INFO = "node_info"          # Node → Server: system capabilities
    NODE_INFO_REQUEST = "node_info_request"  # Server → Node: request capabilities

    # Action dispatch
    ACTION_REQUEST = "action_request"    # Server → Node: execute an action
    ACTION_RESULT = "action_result"      # Node → Server: action completion
    ACTION_PROGRESS = "action_progress"  # Node → Server: interim progress
    ACTION_CANCEL = "action_cancel"      # Server → Node: cancel running action

    # Screen capture
    SCREENSHOT_REQUEST = "screenshot_request"  # Server → Node: request screenshot
    SCREENSHOT_RESPONSE = "screenshot_response"  # Node → Server: screenshot data

    # Grounding
    GROUNDING_REQUEST = "grounding_request"    # Server → Node: request UI grounding
    GROUNDING_RESPONSE = "grounding_response"  # Node → Server: grounded elements

    # Error
    ERROR = "error"  # Either direction: error notification


# ── Action Types ─────────────────────────────────────────────────────────

class ActionType(str, Enum):
    """Types of actions a desktop node can execute."""

    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    KEY_PRESS = "key_press"
    HOTKEY = "hotkey"
    SCROLL = "scroll"
    DRAG = "drag"
    MOVE = "move"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    OPEN_APP = "open_app"
    SWITCH_APP = "switch_app"
    GROUNDING = "grounding"
    CUSTOM_CODE = "custom_code"


# ── Action Status ────────────────────────────────────────────────────────

class ActionStatus(str, Enum):
    """Status of a dispatched action."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


# ── Node Status ──────────────────────────────────────────────────────────

class NodeStatus(str, Enum):
    """Status of a desktop node."""

    CONNECTING = "connecting"
    ONLINE = "online"
    BUSY = "busy"
    IDLE = "idle"
    OFFLINE = "offline"
    ERROR = "error"


# ── Message Data Classes ─────────────────────────────────────────────────

@dataclass
class BaseMessage:
    """Base message with common fields."""
    type: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message_id: str = ""


@dataclass
class HelloMessage(BaseMessage):
    """Initial handshake from node to server."""
    type: str = MessageType.HELLO
    node_id: str = ""
    node_name: str = ""
    version: str = "0.1.0"
    token: str = ""


@dataclass
class WelcomeMessage(BaseMessage):
    """Server response to handshake."""
    type: str = MessageType.WELCOME
    node_id: str = ""
    session_id: str = ""
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class HeartbeatMessage(BaseMessage):
    """Periodic heartbeat from node."""
    type: str = MessageType.HEARTBEAT
    node_id: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    active_actions: int = 0


@dataclass
class NodeInfoMessage(BaseMessage):
    """System capabilities from node."""
    type: str = MessageType.NODE_INFO
    node_id: str = ""
    node_name: str = ""
    os_name: str = ""
    os_version: str = ""
    python_version: str = ""
    screen_width: int = 0
    screen_height: int = 0
    cpu_count: int = 0
    total_memory_mb: int = 0
    gpu_info: list[dict[str, Any]] = field(default_factory=list)
    installed_apps: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    status: str = NodeStatus.ONLINE


@dataclass
class ActionRequest(BaseMessage):
    """Server requests node to execute an action."""
    type: str = MessageType.ACTION_REQUEST
    action_id: str = ""
    action_type: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    priority: int = 0


@dataclass
class ActionResult(BaseMessage):
    """Node reports action completion."""
    type: str = MessageType.ACTION_RESULT
    action_id: str = ""
    status: str = ActionStatus.COMPLETED
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    duration_ms: float = 0.0

    @property
    def success(self) -> bool:
        """Whether the action completed successfully."""
        return self.status == ActionStatus.COMPLETED


@dataclass
class ScreenshotRequest(BaseMessage):
    """Server requests a screenshot."""
    type: str = MessageType.SCREENSHOT_REQUEST
    request_id: str = ""
    quality: int = 85
    region: Optional[list[int]] = None  # [x, y, w, h]


@dataclass
class ScreenshotResponse(BaseMessage):
    """Node sends screenshot data."""
    type: str = MessageType.SCREENSHOT_RESPONSE
    request_id: str = ""
    image_base64: str = ""
    width: int = 0
    height: int = 0
    format: str = "jpeg"


@dataclass
class GroundingRequest(BaseMessage):
    """Server requests UI element grounding."""
    type: str = MessageType.GROUNDING_REQUEST
    request_id: str = ""
    image_base64: str = ""
    instruction: str = ""  # Natural language instruction for grounding


@dataclass
class GroundingResponse(BaseMessage):
    """Node sends grounded UI elements."""
    type: str = MessageType.GROUNDING_RESPONSE
    request_id: str = ""
    elements: list[dict[str, Any]] = field(default_factory=list)
    annotated_image_base64: str = ""


@dataclass
class ErrorMessage(BaseMessage):
    """Error notification."""
    type: str = MessageType.ERROR
    code: str = ""
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)


# ── Serialization Helpers ────────────────────────────────────────────────

_MESSAGE_CLASSES: dict[str, type] = {
    MessageType.HELLO: HelloMessage,
    MessageType.WELCOME: WelcomeMessage,
    MessageType.HEARTBEAT: HeartbeatMessage,
    MessageType.HEARTBEAT_ACK: BaseMessage,
    MessageType.NODE_INFO: NodeInfoMessage,
    MessageType.ACTION_REQUEST: ActionRequest,
    MessageType.ACTION_RESULT: ActionResult,
    MessageType.ACTION_PROGRESS: BaseMessage,
    MessageType.ACTION_CANCEL: BaseMessage,
    MessageType.SCREENSHOT_REQUEST: ScreenshotRequest,
    MessageType.SCREENSHOT_RESPONSE: ScreenshotResponse,
    MessageType.GROUNDING_REQUEST: GroundingRequest,
    MessageType.GROUNDING_RESPONSE: GroundingResponse,
    MessageType.ERROR: ErrorMessage,
}


def serialize_message(msg: BaseMessage) -> str:
    """Serialize a message to JSON string."""
    import json
    return json.dumps(_message_to_dict(msg), ensure_ascii=False)


def deserialize_message(data: str | bytes) -> BaseMessage:
    """Deserialize a JSON string to the appropriate message class."""
    import json
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    raw: dict[str, Any] = json.loads(data)
    msg_type = raw.get("type", "")
    msg_cls = _MESSAGE_CLASSES.get(msg_type, BaseMessage)
    return msg_cls(**{k: v for k, v in raw.items() if k in msg_cls.__dataclass_fields__})


def _message_to_dict(msg: BaseMessage) -> dict[str, Any]:
    """Convert a message dataclass to a plain dict, excluding None values."""
    from dataclasses import fields
    result: dict[str, Any] = {}
    for f in fields(msg):
        val = getattr(msg, f.name)
        if val is not None:
            result[f.name] = val
    return result