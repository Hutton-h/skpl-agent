"""Desktop Node configuration — loaded from environment and CLI args.

All configuration can be set via environment variables (SKPL_DN_ prefix)
or passed programmatically. CLI args override environment variables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DesktopNodeConfig:
    """Configuration for a SKPL Desktop Node.

    Attributes:
        server_url: WebSocket URL of the control center.
        token: JWT authentication token.
        node_name: Human-readable node name (default: hostname).
        node_id: Unique node identifier (auto-generated if None).
        register: Whether to register this node with the control center.
        reconnect_max_attempts: Max reconnection attempts (-1 = infinite).
        reconnect_base_delay: Base delay for exponential backoff (seconds).
        reconnect_max_delay: Maximum delay between reconnection attempts.
        heartbeat_interval: Seconds between heartbeat messages.
        heartbeat_timeout: Seconds before considering connection dead.
        data_dir: Directory for node-local data (screenshots, logs, etc.).
        max_concurrent_actions: Max simultaneous actions this node can execute.
        allowed_apps: Whitelist of apps this node can interact with (empty = all).
        denied_apps: Blacklist of apps this node cannot interact with.
        ocr_enabled: Whether OCR augmentation is enabled.
        ocr_server_url: URL of the OCR server for text extraction.
        grounding_enabled: Whether UI grounding (OmniParser) is enabled.
        grounding_model: Model name for UI grounding.
        grounding_device: Device for grounding model (cpu/cuda/mps).
        screen_capture_method: Method for screen capture (pyautogui/mss/pil).
        screen_capture_quality: JPEG quality for screenshot compression (1-100).
        log_level: Log level for the node.
        log_dir: Directory for node log files.
    """

    # Connection
    server_url: str = "ws://localhost:8000"
    token: str = ""
    node_name: str = ""
    node_id: Optional[str] = None
    register: bool = False

    # Reconnection
    reconnect_max_attempts: int = -1
    reconnect_base_delay: float = 1.0
    reconnect_max_delay: float = 60.0

    # Heartbeat
    heartbeat_interval: float = 10.0
    heartbeat_timeout: float = 30.0

    # Data
    data_dir: Path = field(default_factory=lambda: Path("data/desktop_node"))

    # Execution
    max_concurrent_actions: int = 3
    allowed_apps: list[str] = field(default_factory=list)
    denied_apps: list[str] = field(default_factory=list)

    # OCR
    ocr_enabled: bool = False
    ocr_server_url: str = ""

    # Grounding
    grounding_enabled: bool = False
    grounding_model: str = "microsoft/OmniParser-v2"
    grounding_device: str = "cpu"

    # Screen capture
    screen_capture_method: str = "pyautogui"
    screen_capture_quality: int = 85

    # Logging
    log_level: str = "info"
    log_dir: Path = field(default_factory=lambda: Path("logs/desktop_node"))

    @classmethod
    def from_env(cls) -> "DesktopNodeConfig":
        """Create config from environment variables."""
        import os
        import socket

        return cls(
            server_url=os.environ.get(
                "SKPL_DN_SERVER_URL", "ws://localhost:8000"
            ),
            token=os.environ.get("SKPL_DN_TOKEN", ""),
            node_name=os.environ.get(
                "SKPL_DN_NODE_NAME", socket.gethostname()
            ),
            node_id=os.environ.get("SKPL_DN_NODE_ID") or None,
            register=os.environ.get("SKPL_DN_REGISTER", "").lower() == "true",
            reconnect_max_attempts=int(
                os.environ.get("SKPL_DN_RECONNECT_MAX_ATTEMPTS", "-1")
            ),
            reconnect_base_delay=float(
                os.environ.get("SKPL_DN_RECONNECT_BASE_DELAY", "1.0")
            ),
            reconnect_max_delay=float(
                os.environ.get("SKPL_DN_RECONNECT_MAX_DELAY", "60.0")
            ),
            heartbeat_interval=float(
                os.environ.get("SKPL_DN_HEARTBEAT_INTERVAL", "10.0")
            ),
            heartbeat_timeout=float(
                os.environ.get("SKPL_DN_HEARTBEAT_TIMEOUT", "30.0")
            ),
            data_dir=Path(
                os.environ.get("SKPL_DN_DATA_DIR", "data/desktop_node")
            ),
            max_concurrent_actions=int(
                os.environ.get("SKPL_DN_MAX_CONCURRENT_ACTIONS", "3")
            ),
            allowed_apps=[
                a.strip()
                for a in os.environ.get("SKPL_DN_ALLOWED_APPS", "").split(",")
                if a.strip()
            ],
            denied_apps=[
                a.strip()
                for a in os.environ.get("SKPL_DN_DENIED_APPS", "").split(",")
                if a.strip()
            ],
            ocr_enabled=os.environ.get("SKPL_DN_OCR_ENABLED", "").lower() == "true",
            ocr_server_url=os.environ.get("SKPL_DN_OCR_SERVER_URL", ""),
            grounding_enabled=os.environ.get(
                "SKPL_DN_GROUNDING_ENABLED", ""
            ).lower() == "true",
            grounding_model=os.environ.get(
                "SKPL_DN_GROUNDING_MODEL", "microsoft/OmniParser-v2"
            ),
            grounding_device=os.environ.get(
                "SKPL_DN_GROUNDING_DEVICE", "cpu"
            ),
            screen_capture_method=os.environ.get(
                "SKPL_DN_SCREEN_CAPTURE_METHOD", "pyautogui"
            ),
            screen_capture_quality=int(
                os.environ.get("SKPL_DN_SCREEN_CAPTURE_QUALITY", "85")
            ),
            log_level=os.environ.get("SKPL_DN_LOG_LEVEL", "info"),
            log_dir=Path(
                os.environ.get("SKPL_DN_LOG_DIR", "logs/desktop_node")
            ),
        )