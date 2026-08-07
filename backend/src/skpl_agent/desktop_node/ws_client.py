"""WebSocket client — secure connection to the SKPL Agent control center.

Handles:
- WebSocket connection lifecycle (connect, reconnect, disconnect)
- JWT authentication handshake
- Message serialization/deserialization
- Event dispatch to registered handlers
- Exponential backoff reconnection
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Callable, Optional

import websockets
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    ConnectionClosedOK,
    WebSocketException,
)

from skpl_agent.desktop_node.config import DesktopNodeConfig
from skpl_agent.desktop_node.events import (
    MessageType,
    BaseMessage,
    HelloMessage,
    WelcomeMessage,
    HeartbeatMessage,
    ActionRequest,
    ActionResult,
    ErrorMessage,
    deserialize_message,
    serialize_message,
)

logger = logging.getLogger(__name__)

# Type aliases
MessageHandler = Callable[[BaseMessage], Any]


class DesktopNodeWSClient:
    """WebSocket client for the SKPL Desktop Node.

    Connects to the control center, authenticates, and handles
    bidirectional message passing.

    Usage:
        >>> config = DesktopNodeConfig(server_url="ws://localhost:8000")
        >>> client = DesktopNodeWSClient(config)
        >>> client.on(MessageType.ACTION_REQUEST, handle_action)
        >>> await client.connect()
        >>> await client.run_forever()
    """

    def __init__(self, config: DesktopNodeConfig) -> None:
        self._config = config
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._session_id: str = ""
        self._node_id: str = config.node_id or str(uuid.uuid4())
        self._connected = False
        self._running = False
        self._reconnect_attempt = 0

        # Message handlers: {message_type: [handler1, handler2, ...]}
        self._handlers: dict[str, list[MessageHandler]] = {}

        # Response futures: {message_id: asyncio.Future}
        self._pending_responses: dict[str, asyncio.Future] = {}

        # Background tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Callbacks
        self._on_connected: list[Callable[[], Any]] = []
        self._on_disconnected: list[Callable[[str], Any]] = []
        self._on_error: list[Callable[[Exception], Any]] = []

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def is_connected(self) -> bool:
        return self._connected and self._ws is not None

    @property
    def reconnect_attempt(self) -> int:
        return self._reconnect_attempt

    # ── Callbacks ────────────────────────────────────────────────────────

    def on_connected(self, callback: Callable[[], Any]) -> None:
        """Register a callback for successful connection."""
        self._on_connected.append(callback)

    def on_disconnected(self, callback: Callable[[str], Any]) -> None:
        """Register a callback for disconnection (receives reason string)."""
        self._on_disconnected.append(callback)

    def on_error(self, callback: Callable[[Exception], Any]) -> None:
        """Register a callback for connection errors."""
        self._on_error.append(callback)

    # ── Message Handlers ─────────────────────────────────────────────────

    def on(self, message_type: str, handler: MessageHandler) -> None:
        """Register a handler for a specific message type.

        Args:
            message_type: Message type string (e.g., "action_request").
            handler: Async or sync callable receiving the deserialized message.
        """
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)

    def off(self, message_type: str, handler: MessageHandler) -> None:
        """Remove a handler for a message type."""
        if message_type in self._handlers:
            self._handlers[message_type].remove(handler)

    # ── Connection Lifecycle ─────────────────────────────────────────────

    async def connect(self) -> bool:
        """Connect to the control center and perform handshake.

        Returns:
            True if connected and authenticated successfully.
        """
        try:
            logger.info(
                "Connecting to %s (node_id=%s)",
                self._config.server_url, self._node_id,
            )

            self._ws = await websockets.connect(
                self._config.server_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10,
                max_size=10 * 1024 * 1024,  # 10MB max message size
            )

            # Send hello/handshake
            hello = HelloMessage(
                node_id=self._node_id,
                node_name=self._config.node_name,
                token=self._config.token,
            )

            await self._ws.send(serialize_message(hello))

            # Wait for welcome
            raw = await asyncio.wait_for(self._ws.recv(), timeout=10.0)
            welcome = deserialize_message(raw)

            if isinstance(welcome, WelcomeMessage):
                self._session_id = welcome.session_id
                self._node_id = welcome.node_id or self._node_id
                self._connected = True
                self._reconnect_attempt = 0

                logger.info(
                    "Connected! session_id=%s node_id=%s",
                    self._session_id, self._node_id,
                )

                # Fire callbacks
                for cb in self._on_connected:
                    try:
                        cb()
                    except Exception as e:
                        logger.error("on_connected callback error: %s", e)

                return True
            else:
                logger.error(
                    "Unexpected handshake response: %s", type(welcome).__name__
                )
                await self.disconnect()
                return False

        except asyncio.TimeoutError:
            logger.error("Connection handshake timed out")
            await self._cleanup()
            return False
        except Exception as e:
            logger.error("Connection failed: %s", e)
            await self._cleanup()
            return False

    async def disconnect(self, reason: str = "client_shutdown") -> None:
        """Gracefully disconnect from the control center."""
        self._running = False
        self._connected = False

        # Cancel background tasks
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()

        await self._cleanup()

        for cb in self._on_disconnected:
            try:
                cb(reason)
            except Exception as e:
                logger.error("on_disconnected callback error: %s", e)

    async def _cleanup(self) -> None:
        """Clean up WebSocket connection."""
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._connected = False

    # ── Main Loop ────────────────────────────────────────────────────────

    async def run_forever(self) -> None:
        """Run the client indefinitely with automatic reconnection."""
        self._running = True

        while self._running:
            if not self.is_connected:
                success = await self.connect()
                if success:
                    self._receive_task = asyncio.create_task(
                        self._receive_loop()
                    )
                else:
                    # Reconnect with backoff
                    if not self._running:
                        break
                    delay = self._compute_backoff()
                    logger.info(
                        "Reconnecting in %.1fs (attempt %d)...",
                        delay, self._reconnect_attempt + 1,
                    )
                    await asyncio.sleep(delay)
                    self._reconnect_attempt += 1

                    # Check max attempts
                    if (
                        self._config.reconnect_max_attempts > 0
                        and self._reconnect_attempt >= self._config.reconnect_max_attempts
                    ):
                        logger.error(
                            "Max reconnect attempts (%d) reached",
                            self._config.reconnect_max_attempts,
                        )
                        break

            # Wait for disconnect or error
            if self._receive_task:
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    break
                except Exception:
                    pass

            self._receive_task = None

    async def stop(self) -> None:
        """Stop the client."""
        self._running = False
        await self.disconnect("client_stopped")

    # ── Message Sending ──────────────────────────────────────────────────

    async def send(self, message: BaseMessage) -> None:
        """Send a message to the control center.

        Raises:
            ConnectionError: If not connected.
        """
        if not self.is_connected or self._ws is None:
            raise ConnectionError("Not connected to control center")

        data = serialize_message(message)
        await self._ws.send(data)

    async def send_and_wait(
        self, message: BaseMessage, timeout: float = 30.0
    ) -> BaseMessage:
        """Send a message and wait for a response.

        Args:
            message: Message to send.
            timeout: Maximum wait time in seconds.

        Returns:
            Response message.

        Raises:
            asyncio.TimeoutError: If no response within timeout.
        """
        if not message.message_id:
            message.message_id = str(uuid.uuid4())

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_responses[message.message_id] = future

        try:
            await self.send(message)
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        finally:
            self._pending_responses.pop(message.message_id, None)

    async def send_action_result(self, result: ActionResult) -> None:
        """Send an action result back to the control center."""
        await self.send(result)

    # ── Message Receiving ────────────────────────────────────────────────

    async def _receive_loop(self) -> None:
        """Main receive loop — deserializes and dispatches messages."""
        while self._connected and self._ws is not None:
            try:
                raw = await self._ws.recv()
                await self._handle_message(raw)
            except ConnectionClosedOK:
                logger.info("Connection closed normally")
                break
            except ConnectionClosedError as e:
                logger.warning("Connection closed with error: %s", e)
                break
            except ConnectionClosed:
                logger.warning("Connection closed")
                break
            except WebSocketException as e:
                logger.error("WebSocket error: %s", e)
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Receive error: %s", e)
                break

        # Connection lost
        self._connected = False
        if self._running:
            for cb in self._on_disconnected:
                try:
                    cb("connection_lost")
                except Exception:
                    pass

    async def _handle_message(self, raw: str | bytes) -> None:
        """Deserialize and dispatch an incoming message."""
        try:
            msg = deserialize_message(raw)
        except Exception as e:
            logger.error("Failed to deserialize message: %s", e)
            return

        # Check if this is a response to a pending request
        if msg.message_id and msg.message_id in self._pending_responses:
            future = self._pending_responses[msg.message_id]
            if not future.done():
                future.set_result(msg)
            return

        # Dispatch to registered handlers
        msg_type = msg.type
        if msg_type in self._handlers:
            for handler in self._handlers[msg_type]:
                try:
                    result = handler(msg)
                    if asyncio.iscoroutine(result):
                        asyncio.create_task(result)
                except Exception as e:
                    logger.error(
                        "Handler error for %s: %s", msg_type, e
                    )

        # Also dispatch to catch-all handler
        if "*" in self._handlers:
            for handler in self._handlers["*"]:
                try:
                    result = handler(msg)
                    if asyncio.iscoroutine(result):
                        asyncio.create_task(result)
                except Exception as e:
                    logger.error("Catch-all handler error: %s", e)

    # ── Reconnection ─────────────────────────────────────────────────────

    def _compute_backoff(self) -> float:
        """Compute exponential backoff delay with jitter."""
        import random

        base = self._config.reconnect_base_delay
        max_delay = self._config.reconnect_max_delay
        attempt = self._reconnect_attempt

        delay = min(base * (2 ** attempt), max_delay)
        jitter = delay * 0.1 * random.random()
        return delay + jitter