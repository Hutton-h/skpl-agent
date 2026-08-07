"""Heartbeat manager — periodic health checks and connection monitoring.

Sends periodic heartbeat messages to the control center and monitors
connection health. If heartbeats are not acknowledged within the timeout,
triggers reconnection.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class HeartbeatManager:
    """Manages periodic heartbeat messages and connection health monitoring.

    Usage:
        >>> hb = HeartbeatManager(
        ...     send_callback=lambda msg: ws.send(msg),
        ...     interval=10.0,
        ...     timeout=30.0,
        ... )
        >>> await hb.start()
        >>> # ... later ...
        >>> await hb.stop()
    """

    def __init__(
        self,
        send_callback: Callable[[str], Any],
        node_id: str = "",
        interval: float = 10.0,
        timeout: float = 30.0,
        on_timeout: Callable[[], Any] | None = None,
    ) -> None:
        self._send = send_callback
        self._node_id = node_id
        self._interval = interval
        self._timeout = timeout
        self._on_timeout = on_timeout

        self._task: Optional[asyncio.Task] = None
        self._last_ack_time: float = 0.0
        self._last_send_time: float = 0.0
        self._running = False
        self._missed_count: int = 0
        self._sent_count: int = 0
        self._ack_count: int = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def missed_count(self) -> int:
        return self._missed_count

    @property
    def is_healthy(self) -> bool:
        """Check if the connection is healthy based on last ACK."""
        if self._last_ack_time == 0.0:
            return True  # Haven't sent yet
        elapsed = time.time() - self._last_ack_time
        return elapsed < self._timeout

    async def start(self) -> None:
        """Start sending periodic heartbeats."""
        if self._running:
            return
        self._running = True
        self._last_ack_time = time.time()
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info(
            "Heartbeat started: interval=%.1fs timeout=%.1fs",
            self._interval, self._timeout,
        )

    async def stop(self) -> None:
        """Stop sending heartbeats."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info(
            "Heartbeat stopped: sent=%d acked=%d missed=%d",
            self._sent_count, self._ack_count, self._missed_count,
        )

    def acknowledge(self) -> None:
        """Record a heartbeat acknowledgment from the server."""
        self._last_ack_time = time.time()
        self._ack_count += 1

    def get_stats(self) -> dict[str, Any]:
        """Return heartbeat statistics."""
        return {
            "sent": self._sent_count,
            "acked": self._ack_count,
            "missed": self._missed_count,
            "last_send": self._last_send_time,
            "last_ack": self._last_ack_time,
            "healthy": self.is_healthy,
            "interval": self._interval,
            "timeout": self._timeout,
        }

    # ── Internal ─────────────────────────────────────────────────────────

    async def _heartbeat_loop(self) -> None:
        """Main heartbeat loop."""
        while self._running:
            try:
                await self._send_heartbeat()
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Heartbeat error: %s", e)
                await asyncio.sleep(1.0)  # Brief pause on error

    async def _send_heartbeat(self) -> None:
        """Send a heartbeat message and check for timeout."""
        import json
        from skpl_agent.desktop_node.node_info import NodeInfoCollector

        # Collect dynamic metrics
        collector = NodeInfoCollector()
        metrics = collector.collect_dynamic()

        heartbeat = {
            "type": "heartbeat",
            "node_id": self._node_id,
            "timestamp": time.time(),
            "cpu_percent": metrics.get("cpu_percent", 0.0),
            "memory_percent": metrics.get("memory_percent", 0.0),
            "disk_percent": metrics.get("disk_percent", 0.0),
            "active_actions": 0,
        }

        self._send(json.dumps(heartbeat))
        self._last_send_time = time.time()
        self._sent_count += 1

        # Check if we missed too many heartbeats
        if self._last_ack_time > 0:
            elapsed = time.time() - self._last_ack_time
            if elapsed > self._timeout:
                self._missed_count += 1
                logger.warning(
                    "Heartbeat timeout: %.1fs since last ACK (threshold: %.1fs)",
                    elapsed, self._timeout,
                )
                if self._on_timeout:
                    try:
                        self._on_timeout()
                    except Exception as e:
                        logger.error("Heartbeat timeout callback failed: %s", e)