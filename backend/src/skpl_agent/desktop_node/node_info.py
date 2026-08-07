"""Node information collection — system capabilities and resource monitoring.

Collects OS, hardware, installed applications, and real-time resource usage
for reporting to the control center.
"""

from __future__ import annotations

import logging
import platform
import socket
import sys
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NodeInfo:
    """Static and dynamic information about a desktop node."""

    # Static (collected once at startup)
    node_id: str = ""
    node_name: str = ""
    os_name: str = ""
    os_version: str = ""
    os_release: str = ""
    python_version: str = ""
    hostname: str = ""
    ip_addresses: list[str] = field(default_factory=list)
    cpu_count: int = 0
    cpu_count_logical: int = 0
    total_memory_mb: int = 0
    screen_width: int = 0
    screen_height: int = 0
    gpu_info: list[dict[str, Any]] = field(default_factory=list)
    installed_apps: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)

    # Dynamic (updated periodically)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    active_actions: int = 0
    uptime_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        from dataclasses import asdict
        return asdict(self)


class NodeInfoCollector:
    """Collects static and dynamic node information."""

    def __init__(self) -> None:
        self._static_info: NodeInfo | None = None
        self._start_time: float = 0.0

    # ── Static Info ──────────────────────────────────────────────────────

    def collect_static(
        self,
        node_id: str = "",
        node_name: str = "",
    ) -> NodeInfo:
        """Collect static system information once at startup."""
        import psutil

        info = NodeInfo(
            node_id=node_id,
            node_name=node_name or socket.gethostname(),
            os_name=platform.system(),
            os_version=platform.version(),
            os_release=platform.release(),
            python_version=sys.version.split()[0],
            hostname=socket.gethostname(),
            ip_addresses=self._collect_ip_addresses(),
            cpu_count=psutil.cpu_count(logical=False) or 1,
            cpu_count_logical=psutil.cpu_count(logical=True) or 1,
            total_memory_mb=int(psutil.virtual_memory().total / (1024 * 1024)),
            screen_width=0,
            screen_height=0,
            gpu_info=self._collect_gpu_info(),
            installed_apps=self._collect_installed_apps(),
            capabilities=self._collect_capabilities(),
        )

        # Screen resolution
        screen_info = self._collect_screen_resolution()
        if screen_info:
            info.screen_width = screen_info[0]
            info.screen_height = screen_info[1]

        self._static_info = info
        self._start_time = self._get_uptime()
        return info

    def get_static(self) -> NodeInfo | None:
        """Return the cached static info."""
        return self._static_info

    # ── Dynamic Info ─────────────────────────────────────────────────────

    def collect_dynamic(self) -> dict[str, Any]:
        """Collect real-time resource usage."""
        import psutil

        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        uptime = self._get_uptime() - self._start_time

        return {
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "disk_percent": disk.percent,
            "uptime_seconds": round(uptime, 1),
        }

    def update_dynamic(
        self, active_actions: int = 0
    ) -> dict[str, Any]:
        """Update dynamic metrics on the cached info and return them."""
        metrics = self.collect_dynamic()
        if self._static_info:
            self._static_info.cpu_percent = metrics["cpu_percent"]
            self._static_info.memory_percent = metrics["memory_percent"]
            self._static_info.disk_percent = metrics["disk_percent"]
            self._static_info.active_actions = active_actions
            self._static_info.uptime_seconds = metrics["uptime_seconds"]
        return metrics

    # ── Private Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _collect_ip_addresses() -> list[str]:
        """Collect non-loopback IP addresses."""
        import socket as _socket
        addresses: list[str] = []
        try:
            hostname = _socket.gethostname()
            for info in _socket.getaddrinfo(hostname, None):
                addr = info[4][0]
                if addr and not addr.startswith("127."):
                    addresses.append(addr)
        except Exception:
            pass
        return list(set(addresses))

    @staticmethod
    def _collect_screen_resolution() -> tuple[int, int] | None:
        """Get primary screen resolution."""
        try:
            import pyautogui
            size = pyautogui.size()
            return (size.width, size.height)
        except Exception:
            try:
                import tkinter as tk
                root = tk.Tk()
                w = root.winfo_screenwidth()
                h = root.winfo_screenheight()
                root.destroy()
                return (w, h)
            except Exception:
                return None

    @staticmethod
    def _collect_gpu_info() -> list[dict[str, Any]]:
        """Collect GPU information if available."""
        gpu_list: list[dict[str, Any]] = []
        try:
            import subprocess
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "path", "win32_VideoController", "get", "name"],
                    capture_output=True, text=True, timeout=5,
                )
                lines = result.stdout.strip().split("\n")[1:]
                for line in lines:
                    name = line.strip()
                    if name and name != "Name":
                        gpu_list.append({"name": name, "platform": "windows"})
        except Exception:
            pass
        return gpu_list

    @staticmethod
    def _collect_installed_apps() -> list[str]:
        """Collect list of installed applications relevant to automation."""
        apps: list[str] = []
        try:
            import os
            if platform.system() == "Windows":
                dirs = [
                    os.environ.get("PROGRAMFILES", "C:\\Program Files"),
                    os.environ.get(
                        "PROGRAMFILES(X86)", "C:\\Program Files (x86)"
                    ),
                ]
                for d in dirs:
                    if os.path.exists(d):
                        for root, _dirs, files in os.walk(d):
                            for f in files:
                                if f.lower().endswith(".exe"):
                                    apps.append(f)
                                    if len(apps) >= 500:  # limit
                                        return sorted(apps)
        except Exception:
            pass
        return sorted(apps)

    @staticmethod
    def _collect_capabilities() -> list[str]:
        """Determine which capabilities this node supports."""
        caps = ["screenshot", "keyboard", "mouse"]
        system = platform.system()

        if system == "Windows":
            caps.append("uia")
            caps.append("win32")
            try:
                import pywinauto
                caps.append("pywinauto")
            except ImportError:
                pass
        elif system == "Darwin":
            caps.append("accessibility")
            caps.append("applescript")
        elif system == "Linux":
            caps.append("atspi")
            caps.append("xdotool")

        try:
            import pyautogui
            caps.append("pyautogui")
        except ImportError:
            pass

        try:
            import mss
            caps.append("mss")
        except ImportError:
            pass

        try:
            import numpy
            caps.append("numpy")
        except ImportError:
            pass

        # Check for GPU
        try:
            import torch
            if torch.cuda.is_available():
                caps.append("cuda")
        except ImportError:
            pass

        return caps

    @staticmethod
    def _get_uptime() -> float:
        """Get system uptime in seconds."""
        try:
            import psutil
            import time
            return time.time() - psutil.boot_time()
        except Exception:
            import time
            return time.time()