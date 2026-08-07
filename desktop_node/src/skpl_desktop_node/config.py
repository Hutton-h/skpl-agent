"""配置管理 — 从环境变量或 .env 文件读取配置."""

from __future__ import annotations

import os
import platform
import socket
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class NodeConfig:
    """桌面节点配置。"""

    # ── 连接配置 ──
    server_url: str = ""  # ws://控制中心IP:8001
    token: str = ""  # JWT 认证令牌
    node_name: str = ""  # 节点名称（默认用主机名）
    node_id: str = ""  # 节点唯一 ID（默认自动生成）

    # ── 心跳配置 ──
    heartbeat_interval: float = 10.0
    heartbeat_timeout: float = 30.0

    # ── 重连配置 ──
    reconnect_enabled: bool = True
    reconnect_max_attempts: int = -1  # -1 = 无限重试
    reconnect_base_delay: float = 1.0
    reconnect_max_delay: float = 60.0

    # ── 并发限制 ──
    max_concurrent_actions: int = 3

    # ── 截图 ──
    screen_capture_quality: int = 85

    # ── OCR ──
    ocr_enabled: bool = False
    ocr_lang: str = "ch"

    # ── 日志 ──
    log_level: str = "info"
    log_dir: str = ""


def load_config(
    server_url: str = "",
    token: str = "",
    node_name: str = "",
) -> NodeConfig:
    """加载配置，优先级：命令行参数 > 环境变量 > 默认值。"""

    def _env(key: str, default: str = "") -> str:
        return os.environ.get(key, default)

    def _env_float(key: str, default: float) -> float:
        try:
            return float(os.environ[key])
        except (KeyError, ValueError):
            return default

    def _env_int(key: str, default: int) -> int:
        try:
            return int(os.environ[key])
        except (KeyError, ValueError):
            return default

    def _env_bool(key: str, default: bool) -> bool:
        val = os.environ.get(key, "").lower()
        if val in ("true", "1", "yes"):
            return True
        if val in ("false", "0", "no"):
            return False
        return default

    return NodeConfig(
        server_url=server_url or _env("SKPL_DN_SERVER_URL"),
        token=token or _env("SKPL_DN_TOKEN"),
        node_name=node_name or _env("SKPL_DN_NODE_NAME") or socket.gethostname(),
        node_id=_env("SKPL_DN_NODE_ID"),
        heartbeat_interval=_env_float("SKPL_DN_HEARTBEAT_INTERVAL", 10.0),
        heartbeat_timeout=_env_float("SKPL_DN_HEARTBEAT_TIMEOUT", 30.0),
        reconnect_enabled=_env_bool("SKPL_DN_RECONNECT_ENABLED", True),
        reconnect_max_attempts=_env_int("SKPL_DN_RECONNECT_MAX_ATTEMPTS", -1),
        reconnect_base_delay=_env_float("SKPL_DN_RECONNECT_BASE_DELAY", 1.0),
        reconnect_max_delay=_env_float("SKPL_DN_RECONNECT_MAX_DELAY", 60.0),
        max_concurrent_actions=_env_int("SKPL_DN_MAX_CONCURRENT_ACTIONS", 3),
        screen_capture_quality=_env_int("SKPL_DN_SCREEN_CAPTURE_QUALITY", 85),
        ocr_enabled=_env_bool("SKPL_DN_OCR_ENABLED", False),
        ocr_lang=_env("SKPL_DN_OCR_LANG", "ch"),
        log_level=_env("SKPL_DN_LOG_LEVEL", "info"),
        log_dir=_env("SKPL_DN_LOG_DIR"),
    )