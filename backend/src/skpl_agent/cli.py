"""SKPL Agent CLI entry point.

Usage::

    skpl-agent                 # start dev server on 0.0.0.0:8000
    skpl-agent --host 0.0.0.0 --port 8080
    python -m skpl_agent       # equivalent to above
"""

from __future__ import annotations

import argparse
import logging
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="skpl-agent",
        description="SKPL Agent — unified agent platform with OpenWolf context + Agent-S capabilities",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("SKPL_HOST", "0.0.0.0"),
        help="Host to bind to (default: 0.0.0.0, env: SKPL_HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("SKPL_PORT", "8000")),
        help="Port to bind to (default: 8000, env: SKPL_PORT)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.environ.get("SKPL_RELOAD", "") in ("1", "true", "yes"),
        help="Enable auto-reload on code changes",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("SKPL_LOG_LEVEL", "info"),
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level (default: info)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    import uvicorn

    uvicorn.run(
        "skpl_agent.app._app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()