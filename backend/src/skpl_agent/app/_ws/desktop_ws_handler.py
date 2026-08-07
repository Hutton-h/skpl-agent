"""Desktop WebSocket handler — server-side endpoint for desktop node connections.

Handles:
- WebSocket connection lifecycle for desktop nodes
- JWT authentication
- Message routing (action dispatch, heartbeat, screenshot, grounding)
- Node registration and session tracking
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from skpl_agent.app._service.desktop_scheduler import (
    ActionPriority,
    DesktopScheduler,
    ScheduledAction,
    ScheduleStatus,
)
from skpl_agent.app._service.node_registry import NodeRegistry, RegisteredNode

logger = logging.getLogger(__name__)


class DesktopWSHandler:
    """Server-side WebSocket handler for desktop node connections.

    Manages WebSocket connections from desktop nodes, handles message
    routing, and integrates with the NodeRegistry and DesktopScheduler.

    Usage:
        >>> handler = DesktopWSHandler(registry, scheduler)
        >>> @app.websocket("/ws/desktop/{node_id}")
        >>> async def desktop_ws(websocket: WebSocket, node_id: str):
        >>>     await handler.handle_connection(websocket, node_id)
    """

    def __init__(
        self,
        registry: NodeRegistry,
        scheduler: DesktopScheduler,
        auth_token: str = "",
        max_message_size: int = 10 * 1024 * 1024,  # 10MB
    ) -> None:
        self._registry = registry
        self._scheduler = scheduler
        self._auth_token = auth_token
        self._max_message_size = max_message_size

        # Message type handlers
        self._handlers: dict[str, callable] = {
            "hello": self._handle_hello,
            "heartbeat": self._handle_heartbeat,
            "node_info": self._handle_node_info,
            "action_result": self._handle_action_result,
            "screenshot_response": self._handle_screenshot_response,
            "grounding_response": self._handle_grounding_response,
            "goodbye": self._handle_goodbye,
            "error": self._handle_error,
        }

        # Pending responses: {request_id: asyncio.Future}
        self._pending: dict[str, asyncio.Future] = {}

    # ── Connection Handler ───────────────────────────────────────────────

    async def handle_connection(
        self, websocket: WebSocket, tenant_id: str = "default"
    ) -> None:
        """Handle a desktop node WebSocket connection.

        Args:
            websocket: The WebSocket connection.
            tenant_id: Tenant for multi-tenant routing.
        """
        await websocket.accept()
        session_id = str(uuid.uuid4())
        node_id = ""
        node_name = "unknown"

        logger.info(
            "Desktop node connected: session=%s tenant=%s",
            session_id, tenant_id,
        )

        try:
            while websocket.client_state == WebSocketState.CONNECTED:
                raw = await websocket.receive_text()

                if len(raw) > self._max_message_size:
                    logger.warning("Message too large from session %s", session_id)
                    continue

                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON from session %s", session_id)
                    continue

                msg_type = msg.get("type", "")
                handler = self._handlers.get(msg_type)

                if handler:
                    try:
                        node_id = msg.get("node_id", node_id)
                        node_name = msg.get("node_name", node_name)
                        await handler(
                            websocket, session_id, node_id, node_name, msg,
                        )
                    except Exception as e:
                        logger.error(
                            "Handler error for %s: %s", msg_type, e,
                        )
                        await self._send_error(
                            websocket, f"Handler error: {e}",
                        )
                else:
                    logger.debug(
                        "Unknown message type: %s from %s", msg_type, node_id,
                    )

        except WebSocketDisconnect:
            logger.info(
                "Desktop node disconnected: %s (%s)", node_name, node_id,
            )
        except Exception as e:
            logger.error("WebSocket error: %s", e)
        finally:
            # Cleanup
            await self._cleanup_node(session_id, node_id)

    # ── Message Handlers ─────────────────────────────────────────────────

    async def _handle_hello(
        self,
        ws: WebSocket,
        session_id: str,
        node_id: str,
        node_name: str,
        msg: dict[str, Any],
    ) -> None:
        """Handle initial handshake from a node."""
        token = msg.get("token", "")

        # Authenticate if token is configured
        if self._auth_token and token != self._auth_token:
            logger.warning("Authentication failed for node %s", node_id)
            await self._send(ws, {
                "type": "error",
                "code": "auth_failed",
                "reason": "Invalid authentication token",
            })
            await ws.close(code=4001, reason="Authentication failed")
            return

        # Register the node
        node = RegisteredNode(
            node_id=node_id or str(uuid.uuid4()),
            node_name=node_name or "unknown",
            session_id=session_id,
            status="connecting",
            os_name=msg.get("os_name", ""),
            version=msg.get("version", "0.1.0"),
            registered_at=datetime.now(timezone.utc),
        )

        await self._registry.register(node)

        # Send welcome
        await self._send(ws, {
            "type": "welcome",
            "node_id": node.node_id,
            "session_id": session_id,
            "config": {
                "heartbeat_interval": 10,
                "max_concurrent_actions": 3,
            },
        })

        logger.info(
            "Node handshake complete: %s (%s)", node.node_name, node.node_id,
        )

    async def _handle_heartbeat(
        self,
        ws: WebSocket,
        session_id: str,
        node_id: str,
        node_name: str,
        msg: dict[str, Any],
    ) -> None:
        """Handle heartbeat from a node."""
        metrics = {
            "cpu_percent": msg.get("cpu_percent", 0.0),
            "memory_percent": msg.get("memory_percent", 0.0),
            "disk_percent": msg.get("disk_percent", 0.0),
            "active_actions": msg.get("active_actions", 0),
        }

        found = await self._registry.heartbeat(node_id, metrics)

        if found:
            await self._send(ws, {
                "type": "heartbeat_ack",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    async def _handle_node_info(
        self,
        ws: WebSocket,
        session_id: str,
        node_id: str,
        node_name: str,
        msg: dict[str, Any],
    ) -> None:
        """Handle node info update."""
        await self._registry.update_node_info(node_id, msg)
        logger.debug("Node info updated: %s", node_id)

    async def _handle_action_result(
        self,
        ws: WebSocket,
        session_id: str,
        node_id: str,
        node_name: str,
        msg: dict[str, Any],
    ) -> None:
        """Handle action result from a node."""
        action_id = msg.get("action_id", "")
        status = msg.get("status", "completed")

        if status == "completed":
            await self._scheduler.on_action_completed(
                action_id, msg.get("result", {}),
            )
        elif status in ("failed", "timed_out"):
            await self._scheduler.on_action_failed(
                action_id, msg.get("error", "Unknown error"),
            )

    async def _handle_screenshot_response(
        self,
        ws: WebSocket,
        session_id: str,
        node_id: str,
        node_name: str,
        msg: dict[str, Any],
    ) -> None:
        """Handle screenshot response."""
        request_id = msg.get("request_id", "")
        if request_id in self._pending:
            future = self._pending.pop(request_id)
            if not future.done():
                future.set_result(msg)

    async def _handle_grounding_response(
        self,
        ws: WebSocket,
        session_id: str,
        node_id: str,
        node_name: str,
        msg: dict[str, Any],
    ) -> None:
        """Handle grounding response."""
        request_id = msg.get("request_id", "")
        if request_id in self._pending:
            future = self._pending.pop(request_id)
            if not future.done():
                future.set_result(msg)

    async def _handle_goodbye(
        self,
        ws: WebSocket,
        session_id: str,
        node_id: str,
        node_name: str,
        msg: dict[str, Any],
    ) -> None:
        """Handle graceful disconnect."""
        logger.info("Node %s saying goodbye", node_id)
        await self._registry.unregister(node_id)

    async def _handle_error(
        self,
        ws: WebSocket,
        session_id: str,
        node_id: str,
        node_name: str,
        msg: dict[str, Any],
    ) -> None:
        """Handle error from a node."""
        logger.error(
            "Node %s error: code=%s reason=%s",
            node_id, msg.get("code", ""), msg.get("reason", ""),
        )

    # ── Action Dispatch ──────────────────────────────────────────────────

    async def dispatch_action(
        self,
        ws: WebSocket,
        action: ScheduledAction,
        node: RegisteredNode,
    ) -> None:
        """Send an action to a specific node."""
        await self._send(ws, {
            "type": "action_request",
            "action_id": action.action_id,
            "action_type": action.action_type,
            "params": action.params,
            "timeout": action.timeout,
            "priority": action.priority.value,
        })

    async def request_screenshot(
        self,
        ws: WebSocket,
        quality: int = 85,
        timeout: float = 10.0,
    ) -> dict[str, Any] | None:
        """Request a screenshot from a node and wait for response.

        Args:
            ws: The WebSocket connection.
            quality: JPEG quality (1-100).
            timeout: Maximum wait time in seconds.

        Returns:
            Screenshot response dict or None on timeout.
        """
        request_id = str(uuid.uuid4())
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future

        try:
            await self._send(ws, {
                "type": "screenshot_request",
                "request_id": request_id,
                "quality": quality,
            })
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning("Screenshot request %s timed out", request_id)
            return None
        finally:
            self._pending.pop(request_id, None)

    async def request_grounding(
        self,
        ws: WebSocket,
        image_base64: str,
        instruction: str = "",
        timeout: float = 30.0,
    ) -> dict[str, Any] | None:
        """Request UI grounding from a node.

        Args:
            ws: The WebSocket connection.
            image_base64: Base64-encoded screenshot.
            instruction: Natural language grounding instruction.
            timeout: Maximum wait time in seconds.

        Returns:
            Grounding response dict or None on timeout.
        """
        request_id = str(uuid.uuid4())
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future

        try:
            await self._send(ws, {
                "type": "grounding_request",
                "request_id": request_id,
                "image_base64": image_base64,
                "instruction": instruction,
            })
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning("Grounding request %s timed out", request_id)
            return None
        finally:
            self._pending.pop(request_id, None)

    # ── Helpers ──────────────────────────────────────────────────────────

    async def _send(self, ws: WebSocket, data: dict[str, Any]) -> None:
        """Send JSON data to the WebSocket."""
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_text(json.dumps(data, ensure_ascii=False))

    async def _send_error(self, ws: WebSocket, reason: str) -> None:
        """Send an error message."""
        await self._send(ws, {
            "type": "error",
            "code": "server_error",
            "reason": reason,
        })

    async def _cleanup_node(
        self, session_id: str, node_id: str,
    ) -> None:
        """Clean up node resources on disconnect."""
        if node_id:
            await self._registry.unregister(node_id)
        else:
            self._registry.unregister_by_session(session_id)