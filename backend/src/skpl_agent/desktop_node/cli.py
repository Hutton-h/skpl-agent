"""SKPL Desktop Node CLI entry point.

Usage::

    skpl-desktop-node --server ws://localhost:8000 --token <jwt>
    skpl-desktop-node --register --name "My Machine"
    skpl-desktop-node --config config.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from skpl_agent.desktop_node.config import DesktopNodeConfig
from skpl_agent.desktop_node.events import (
    MessageType,
    ActionRequest,
    ActionResult,
    ActionStatus,
    GroundingRequest,
    GroundingResponse,
    ScreenshotRequest,
    ScreenshotResponse,
    NodeInfoMessage,
    serialize_message,
    deserialize_message,
)
from skpl_agent.desktop_node.executor import ActionExecutor
from skpl_agent.desktop_node.grounding import create_grounding_model
from skpl_agent.desktop_node.heartbeat import HeartbeatManager
from skpl_agent.desktop_node.node_info import NodeInfoCollector
from skpl_agent.desktop_node.screen import ScreenCapture
from skpl_agent.desktop_node.security import SecurityPolicy
from skpl_agent.desktop_node.ws_client import DesktopNodeWSClient


def main() -> None:
    """CLI entry point for the desktop node."""
    parser = _build_parser()
    args = parser.parse_args()

    _setup_logging(args.log_level)
    logger = logging.getLogger("skpl_desktop_node")

    config = _build_config(args)

    logger.info("SKPL Desktop Node v0.2.0")
    logger.info("Server: %s", config.server_url)
    logger.info("Node: %s (id=%s)", config.node_name, config.node_id)
    logger.info("Capabilities: pyautogui, screenshot, keyboard, mouse")

    if not config.token:
        logger.warning(
            "No authentication token provided. "
            "Set SKPL_DESKTOP_TOKEN or use --token."
        )

    try:
        asyncio.run(_run_node(config, logger))
    except KeyboardInterrupt:
        logger.info("Node stopped by user.")
    except Exception as exc:
        logger.critical("Node crashed: %s", exc, exc_info=True)
        sys.exit(1)


# ── Builder Functions ────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="skpl-desktop-node",
        description="SKPL Desktop Node — edge node for desktop automation",
    )

    # Connection
    parser.add_argument(
        "--server",
        default=os.environ.get("SKPL_DESKTOP_SERVER", "ws://localhost:8000"),
        help="WebSocket URL of the control center",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("SKPL_DESKTOP_TOKEN", ""),
        help="JWT authentication token",
    )
    parser.add_argument(
        "--name",
        default=os.environ.get("SKPL_DESKTOP_NAME", ""),
        help="Human-readable node name (default: hostname)",
    )
    parser.add_argument(
        "--register",
        action="store_true",
        help="Register this node with the control center",
    )

    # Reconnection
    parser.add_argument(
        "--reconnect-max-attempts",
        type=int,
        default=int(os.environ.get("SKPL_DN_RECONNECT_MAX_ATTEMPTS", "-1")),
        help="Max reconnection attempts (-1 = infinite)",
    )

    # Security
    parser.add_argument(
        "--allow-custom-code",
        action="store_true",
        help="Allow execution of custom Python code (DANGEROUS)",
    )
    parser.add_argument(
        "--allowed-apps",
        default=os.environ.get("SKPL_DN_ALLOWED_APPS", ""),
        help="Comma-separated list of allowed application names",
    )
    parser.add_argument(
        "--denied-apps",
        default=os.environ.get("SKPL_DN_DENIED_APPS", ""),
        help="Comma-separated list of denied application names",
    )

    # Grounding
    parser.add_argument(
        "--grounding-model",
        default=os.environ.get("SKPL_DN_GROUNDING_MODEL", "simple"),
        choices=["simple", "omniparser", "none"],
        help="UI grounding model type",
    )
    parser.add_argument(
        "--grounding-device",
        default=os.environ.get("SKPL_DN_GROUNDING_DEVICE", "cpu"),
        choices=["cpu", "cuda", "mps"],
        help="Device for grounding model",
    )

    # Screen capture
    parser.add_argument(
        "--capture-backend",
        default=os.environ.get("SKPL_DN_SCREEN_CAPTURE_METHOD", "mss"),
        choices=["mss", "pyautogui", "pil"],
        help="Screen capture backend",
    )

    # Logging
    parser.add_argument(
        "--log-level",
        default=os.environ.get("SKPL_DN_LOG_LEVEL", "info"),
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level",
    )

    return parser


def _build_config(args: argparse.Namespace) -> DesktopNodeConfig:
    """Build DesktopNodeConfig from CLI args and environment."""
    config = DesktopNodeConfig.from_env()

    # Override with CLI args
    if args.server:
        config.server_url = args.server
    if args.token:
        config.token = args.token
    if args.name:
        config.node_name = args.name
    if args.register:
        config.register = True
    if args.reconnect_max_attempts >= 0:
        config.reconnect_max_attempts = args.reconnect_max_attempts
    if args.allow_custom_code:
        config.allowed_apps = []  # Allow all
    if args.allowed_apps:
        config.allowed_apps = [
            a.strip() for a in args.allowed_apps.split(",") if a.strip()
        ]
    if args.denied_apps:
        config.denied_apps = [
            a.strip() for a in args.denied_apps.split(",") if a.strip()
        ]
    if args.grounding_model:
        config.grounding_model = args.grounding_model
    if args.grounding_device:
        config.grounding_device = args.grounding_device
    if args.capture_backend:
        config.screen_capture_method = args.capture_backend

    return config


def _setup_logging(level: str) -> None:
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ── Main Node Runner ─────────────────────────────────────────────────────

async def _run_node(
    config: DesktopNodeConfig, logger: logging.Logger
) -> None:
    """Initialize and run the desktop node."""
    # Ensure data directories exist
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.log_dir.mkdir(parents=True, exist_ok=True)

    # Collect node info
    collector = NodeInfoCollector()
    node_info = collector.collect_static(
        node_id=config.node_id or "",
        node_name=config.node_name,
    )
    config.node_id = node_info.node_id or config.node_id
    logger.info(
        "System: %s %s | CPU: %d cores | Memory: %d MB",
        node_info.os_name, node_info.os_release,
        node_info.cpu_count_logical, node_info.total_memory_mb,
    )
    logger.info("Screen: %dx%d", node_info.screen_width, node_info.screen_height)

    # Initialize components
    security_policy = SecurityPolicy(
        allowed_apps=config.allowed_apps,
        denied_apps=config.denied_apps,
        allow_custom_code=config.allow_custom_code,
    )
    executor = ActionExecutor(policy=security_policy)
    screen_capture = ScreenCapture(
        backend=config.screen_capture_method,
        quality=config.screen_capture_quality,
    )
    grounding_model = create_grounding_model(
        model_type=config.grounding_model,
        device=config.grounding_device,
    )

    # Initialize WebSocket client
    client = DesktopNodeWSClient(config)

    # ── Register message handlers ────────────────────────────────────────

    # Action dispatch
    async def handle_action_request(msg: ActionRequest) -> None:
        logger.info(
            "Action received: id=%s type=%s",
            msg.action_id, msg.action_type,
        )
        result = await executor.execute(msg)
        await client.send(result)
        logger.info(
            "Action completed: id=%s status=%s (%.0fms)",
            msg.action_id, result.status, result.duration_ms,
        )

    client.on(MessageType.ACTION_REQUEST, handle_action_request)

    # Screenshot request
    async def handle_screenshot_request(msg: ScreenshotRequest) -> None:
        logger.debug("Screenshot requested: id=%s", msg.request_id)
        try:
            b64 = screen_capture.capture_base64(
                region=tuple(msg.region) if msg.region else None,
                img_format="jpeg",
            )
            size = screen_capture.get_screen_size()
            response = ScreenshotResponse(
                request_id=msg.request_id,
                image_base64=b64,
                width=size[0],
                height=size[1],
            )
            await client.send(response)
        except Exception as e:
            logger.error("Screenshot failed: %s", e)

    client.on(MessageType.SCREENSHOT_REQUEST, handle_screenshot_request)

    # Grounding request
    async def handle_grounding_request(msg: GroundingRequest) -> None:
        logger.info("Grounding requested: id=%s", msg.request_id)
        try:
            result = grounding_model.ground(
                image_base64=msg.image_base64,
                instruction=msg.instruction,
            )
            response = GroundingResponse(
                request_id=msg.request_id,
                elements=result.elements,
                annotated_image_base64=result.annotated_image_base64,
            )
            await client.send(response)
            logger.info(
                "Grounding done: %d elements (%.0fms)",
                len(result.elements), result.latency_ms,
            )
        except Exception as e:
            logger.error("Grounding failed: %s", e)

    client.on(MessageType.GROUNDING_REQUEST, handle_grounding_request)

    # Node info request
    async def handle_node_info_request(msg) -> None:
        logger.debug("Node info requested")
        metrics = collector.collect_dynamic()
        info = NodeInfoMessage(
            node_id=config.node_id or "",
            node_name=config.node_name,
            os_name=node_info.os_name,
            os_version=node_info.os_version,
            python_version=node_info.python_version,
            screen_width=node_info.screen_width,
            screen_height=node_info.screen_height,
            cpu_count=node_info.cpu_count_logical,
            total_memory_mb=node_info.total_memory_mb,
            installed_apps=node_info.installed_apps[:50],  # limit
            capabilities=node_info.capabilities,
            cpu_percent=metrics.get("cpu_percent", 0.0),
            memory_percent=metrics.get("memory_percent", 0.0),
            active_actions=executor.active_count,
        )
        await client.send(info)

    client.on(MessageType.NODE_INFO_REQUEST, handle_node_info_request)

    # ── Heartbeat setup ──────────────────────────────────────────────────

    heartbeat = HeartbeatManager(
        send_callback=lambda msg: asyncio.create_task(_send_raw(client, msg)),
        node_id=config.node_id or "",
        interval=config.heartbeat_interval,
        timeout=config.heartbeat_timeout,
        on_timeout=lambda: logger.warning("Heartbeat timeout — connection may be dead"),
    )

    # Heartbeat ACK handler
    def handle_heartbeat_ack(msg) -> None:
        heartbeat.acknowledge()

    client.on(MessageType.HEARTBEAT_ACK, handle_heartbeat_ack)

    # ── Connection callbacks ─────────────────────────────────────────────

    async def on_connected() -> None:
        logger.info("Connected to control center!")
        await heartbeat.start()

        # Send node info on connect
        info_msg = NodeInfoMessage(
            node_id=config.node_id or "",
            node_name=config.node_name,
            os_name=node_info.os_name,
            os_version=node_info.os_version,
            python_version=node_info.python_version,
            screen_width=node_info.screen_width,
            screen_height=node_info.screen_height,
            cpu_count=node_info.cpu_count_logical,
            total_memory_mb=node_info.total_memory_mb,
            capabilities=node_info.capabilities,
        )
        await client.send(info_msg)

    async def on_disconnected(reason: str) -> None:
        logger.warning("Disconnected: %s", reason)
        await heartbeat.stop()

    client.on_connected(lambda: asyncio.create_task(on_connected()))
    client.on_disconnected(lambda r: asyncio.create_task(on_disconnected(r)))

    # ── Run ──────────────────────────────────────────────────────────────

    # Graceful shutdown
    loop = asyncio.get_event_loop()

    def shutdown() -> None:
        logger.info("Shutting down...")
        asyncio.create_task(_shutdown(client, heartbeat, executor, grounding_model))

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler for SIGTERM
            pass

    try:
        await client.run_forever()
    except asyncio.CancelledError:
        pass
    finally:
        await _shutdown(client, heartbeat, executor, grounding_model)


async def _send_raw(client: DesktopNodeWSClient, message: str) -> None:
    """Send a raw JSON string through the WebSocket."""
    if client.is_connected and client._ws is not None:
        await client._ws.send(message)


async def _shutdown(
    client: DesktopNodeWSClient,
    heartbeat: HeartbeatManager,
    executor: ActionExecutor,
    grounding_model,
) -> None:
    """Clean shutdown sequence."""
    await heartbeat.stop()
    executor.shutdown()
    grounding_model.unload()
    await client.disconnect("shutdown")


if __name__ == "__main__":
    main()