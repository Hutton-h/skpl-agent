"""WebSocket 节点客户端 — 连接到控制中心，接收指令并执行动作."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from .actions import dispatch_action, execute_screenshot, get_system_info
from .config import NodeConfig

logger = logging.getLogger(__name__)


class DesktopNode:
    """桌面节点客户端。

    通过 WebSocket 连接到控制中心，执行以下操作：
    - 握手认证（hello）
    - 定时心跳（heartbeat）
    - 接收并执行动作（action_request → action_result）
    - 响应截图请求（screenshot_request → screenshot_response）
    """

    def __init__(self, config: NodeConfig) -> None:
        self._config = config
        self._ws = None
        self._running = False
        self._node_id = config.node_id or str(uuid.uuid4())[:8]
        self._active_actions = 0
        self._action_lock = asyncio.Lock()

    # ── 公共 API ───────────────────────────────────────────────────────

    async def start(self) -> None:
        """启动节点，自动重连。"""
        self._running = True
        attempt = 0

        while self._running:
            try:
                attempt += 1
                logger.info(
                    "正在连接控制中心 %s (第 %d 次尝试)...",
                    self._config.server_url, attempt,
                )
                await self._connect()
                attempt = 0  # 连接成功，重置计数
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("连接失败: %s", e)
                if not self._running:
                    break
                delay = min(
                    self._config.reconnect_base_delay * (2 ** (attempt - 1)),
                    self._config.reconnect_max_delay,
                )
                logger.info("%d 秒后重试...", int(delay))
                await asyncio.sleep(delay)

    async def stop(self) -> None:
        """停止节点。"""
        self._running = False
        if self._ws:
            try:
                await self._send({"type": "goodbye", "node_id": self._node_id})
                await self._ws.close()
            except Exception:
                pass

    # ── 内部方法 ───────────────────────────────────────────────────────

    async def _connect(self) -> None:
        """建立 WebSocket 连接并开始消息循环。"""
        ws_url = self._config.server_url
        if not ws_url.startswith(("ws://", "wss://")):
            ws_url = f"ws://{ws_url}"
        # 添加节点 ID 路径
        ws_url = ws_url.rstrip("/") + f"/ws/desktop/{self._node_id}"

        # 添加 token 到查询参数
        if "?" in ws_url:
            ws_url += f"&token={self._config.token}"
        else:
            ws_url += f"?token={self._config.token}"

        async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
            self._ws = ws
            logger.info("WebSocket 已连接到 %s", ws_url)

            # 发送握手消息
            await self._send_hello()

            # 启动心跳任务
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            try:
                # 消息循环
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning("收到无效 JSON")
                        continue

                    await self._handle_message(msg)

            except ConnectionClosed:
                logger.warning("连接已断开")
            finally:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

    async def _send_hello(self) -> None:
        """发送握手消息。"""
        info = get_system_info()
        await self._send({
            "type": "hello",
            "node_id": self._node_id,
            "node_name": self._config.node_name,
            "token": self._config.token,
            "os_name": info.get("os_name", "Windows"),
            "version": "0.2.0",
            "hostname": info.get("hostname", ""),
            "python_version": info.get("python_version", ""),
            "cpu_count": info.get("cpu_count", 0),
            "total_memory_mb": info.get("total_memory_mb", 0),
            "screen_width": info.get("screen_width", 0),
            "screen_height": info.get("screen_height", 0),
        })
        logger.info("握手消息已发送: node_id=%s name=%s", self._node_id, self._config.node_name)

    async def _heartbeat_loop(self) -> None:
        """定时发送心跳。"""
        while self._running and self._ws:
            try:
                info = get_system_info()
                await self._send({
                    "type": "heartbeat",
                    "node_id": self._node_id,
                    "node_name": self._config.node_name,
                    "cpu_percent": info.get("cpu_percent", 0.0),
                    "memory_percent": info.get("memory_percent", 0.0),
                    "disk_percent": info.get("disk_percent", 0.0),
                    "active_actions": self._active_actions,
                })
            except Exception as e:
                logger.warning("心跳发送失败: %s", e)
                break
            await asyncio.sleep(self._config.heartbeat_interval)

    async def _handle_message(self, msg: dict[str, Any]) -> None:
        """处理来自控制中心的消息。"""
        msg_type = msg.get("type", "")

        if msg_type == "welcome":
            logger.info(
                "握手成功! node_id=%s, 心跳间隔=%ds",
                msg.get("node_id", "?"),
                msg.get("config", {}).get("heartbeat_interval", 10),
            )

        elif msg_type == "heartbeat_ack":
            logger.debug("心跳确认")

        elif msg_type == "action_request":
            asyncio.create_task(self._handle_action(msg))

        elif msg_type == "screenshot_request":
            asyncio.create_task(self._handle_screenshot_request(msg))

        elif msg_type == "error":
            logger.error("控制中心错误: %s", msg.get("reason", "未知错误"))

        else:
            logger.debug("未知消息类型: %s", msg_type)

    async def _handle_action(self, msg: dict[str, Any]) -> None:
        """处理动作请求。"""
        action_id = msg.get("action_id", "")
        action_type = msg.get("action_type", "")
        params = msg.get("params", {})

        async with self._action_lock:
            self._active_actions += 1

        try:
            logger.info("执行动作: %s (id=%s)", action_type, action_id)
            result = await asyncio.to_thread(dispatch_action, action_type, params)
            result["action_id"] = action_id
            result["action_type"] = action_type

            await self._send({
                "type": "action_result",
                "action_id": action_id,
                "status": "completed" if result.get("success") else "failed",
                "result": result.get("data", {}),
                "error": result.get("error", ""),
            })
        except Exception as e:
            logger.error("动作执行异常: %s", e)
            await self._send({
                "type": "action_result",
                "action_id": action_id,
                "status": "failed",
                "error": str(e),
            })
        finally:
            async with self._action_lock:
                self._active_actions -= 1

    async def _handle_screenshot_request(self, msg: dict[str, Any]) -> None:
        """处理截图请求。"""
        request_id = msg.get("request_id", "")
        quality = msg.get("quality", 85)

        try:
            result = await asyncio.to_thread(execute_screenshot, quality)
            await self._send({
                "type": "screenshot_response",
                "request_id": request_id,
                "image_base64": result.get("data", {}).get("image_base64", ""),
                "width": result.get("data", {}).get("width", 0),
                "height": result.get("data", {}).get("height", 0),
            })
        except Exception as e:
            logger.error("截图失败: %s", e)
            await self._send({
                "type": "screenshot_response",
                "request_id": request_id,
                "error": str(e),
            })

    async def _send(self, data: dict[str, Any]) -> None:
        """发送 JSON 消息到 WebSocket。"""
        if self._ws:
            try:
                await self._ws.send(json.dumps(data, ensure_ascii=False))
            except Exception:
                pass