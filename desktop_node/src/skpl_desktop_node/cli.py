"""CLI 入口 — 启动桌面节点。

用法:
    python -m skpl_desktop_node --server ws://控制中心IP:8001 --token 你的JWT令牌
    python -m skpl_desktop_node --server ws://控制中心IP:8001 --token 你的JWT令牌 --name 我的电脑
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from .config import load_config, NodeConfig
from .node import DesktopNode


def setup_logging(config: NodeConfig) -> None:
    """配置日志输出。"""
    level = getattr(logging, config.log_level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if config.log_dir:
        log_dir = Path(config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / "desktop_node.log", encoding="utf-8",
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


def main() -> None:
    """CLI 主入口。"""
    parser = argparse.ArgumentParser(
        description="SKPL Desktop Node v0.2.0 — 桌面自动化节点",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m skpl_desktop_node --server ws://192.168.1.100:8001 --token abc123
  python -m skpl_desktop_node --server ws://vps.example.com:8001 --token abc123 --name 办公室电脑

环境变量:
  SKPL_DN_SERVER_URL  服务器地址
  SKPL_DN_TOKEN       JWT 令牌
  SKPL_DN_NODE_NAME   节点名称
        """,
    )
    parser.add_argument(
        "--server", "-s",
        default=os.environ.get("SKPL_DN_SERVER_URL", ""),
        help="控制中心 WebSocket 地址 (如 ws://192.168.1.100:8001)",
    )
    parser.add_argument(
        "--token", "-t",
        default=os.environ.get("SKPL_DN_TOKEN", ""),
        help="JWT 认证令牌",
    )
    parser.add_argument(
        "--name", "-n",
        default=os.environ.get("SKPL_DN_NODE_NAME", ""),
        help="节点名称 (默认使用主机名)",
    )
    parser.add_argument(
        "--log-level", "-l",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="日志级别 (默认: info)",
    )

    args = parser.parse_args()

    # 加载配置
    config = load_config(
        server_url=args.server,
        token=args.token,
        node_name=args.name,
    )
    config.log_level = args.log_level

    # 验证必需参数
    if not config.server_url:
        print("=" * 60)
        print("  SKPL Desktop Node v0.2.0")
        print("=" * 60)
        print()
        print("  错误: 未提供服务器地址!")
        print()
        print("  使用方法:")
        print("    python -m skpl_desktop_node --server 服务器地址 --token JWT令牌")
        print()
        print("  示例:")
        print("    python -m skpl_desktop_node --server ws://192.168.1.100:8001 --token abc123")
        print("    python -m skpl_desktop_node --server ws://vps.example.com:8001 --token abc123 --name 我的电脑")
        print()
        print("  也可以通过环境变量配置:")
        print("    set SKPL_DN_SERVER_URL=ws://192.168.1.100:8001")
        print("    set SKPL_DN_TOKEN=abc123")
        print("    python -m skpl_desktop_node")
        print()
        sys.exit(1)

    if not config.token:
        print("=" * 60)
        print("  SKPL Desktop Node v0.2.0")
        print("=" * 60)
        print()
        print("  错误: 未提供 JWT 令牌!")
        print()
        print("  请使用 --token 参数或设置 SKPL_DN_TOKEN 环境变量")
        print()
        sys.exit(1)

    # 设置日志
    setup_logging(config)
    logger = logging.getLogger(__name__)

    # 打印启动信息
    print("=" * 60)
    print("  SKPL Desktop Node v0.2.0")
    print("=" * 60)
    print(f"  节点名称: {config.node_name}")
    print(f"  节点 ID:  {config.node_id or '(自动生成)'}")
    print(f"  服务器:   {config.server_url}")
    print(f"  心跳间隔: {config.heartbeat_interval}s")
    print("=" * 60)
    print()
    print("  正在启动... 按 Ctrl+C 停止")
    print()

    # 创建节点
    node = DesktopNode(config)

    # 处理信号
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if sys.platform == "win32":
        # Windows 下使用不同的信号处理
        import signal as _signal
        try:
            loop.add_signal_handler(
                _signal.SIGINT, lambda: asyncio.create_task(node.stop()),
            )
        except NotImplementedError:
            pass
    else:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig, lambda: asyncio.create_task(node.stop()),
            )

    try:
        loop.run_until_complete(node.start())
    except KeyboardInterrupt:
        print("\n正在停止...")
        loop.run_until_complete(node.stop())
    finally:
        loop.close()
        print("节点已停止。")