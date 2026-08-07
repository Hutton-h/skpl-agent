"""SKPL-specific OpenTelemetry span definitions.

This module provides factory functions that create SKPL-domain spans
for operations that are not covered by the generic AgentScope tracing
middleware.  Each function returns a properly configured span with
start/end timestamps, attributes, and status management.

Usage:
    from skpl_agent.middleware._tracing._skpl_spans import context_scan_span

    with context_scan_span(session_id="sess-1", root_path="/project") as span:
        # ... perform context scan ...
        pass  # span auto-closes on exit
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Generator, Optional

from opentelemetry import trace
from opentelemetry.trace import Span, SpanKind, StatusCode, get_tracer

logger = logging.getLogger(__name__)

# ── Tracer instance ──────────────────────────────────────────────────────────
_SKPL_TRACER_NAME = "skpl-agent"
_tracer = get_tracer(_SKPL_TRACER_NAME)

# ── Span attribute names ─────────────────────────────────────────────────────

class SKPLSpanAttributes:
    """Attribute keys used across SKPL spans."""

    # Context scan
    CONTEXT_SCAN_ROOT_PATH = "skpl.context.scan.root_path"
    CONTEXT_SCAN_MODE = "skpl.context.scan.mode"
    CONTEXT_SCAN_FILES_SCANNED = "skpl.context.scan.files_scanned"
    CONTEXT_SCAN_SYMBOLS_EXTRACTED = "skpl.context.scan.symbols_extracted"
    CONTEXT_SCAN_DURATION_SECONDS = "skpl.context.scan.duration_seconds"

    # Desktop action
    DESKTOP_ACTION_TYPE = "skpl.desktop.action.type"
    DESKTOP_ACTION_NODE_ID = "skpl.desktop.node_id"
    DESKTOP_ACTION_TARGET = "skpl.desktop.action.target"
    DESKTOP_ACTION_DURATION_MS = "skpl.desktop.action.duration_ms"

    # Firecrawl request
    FIRECRAWL_URL = "skpl.firecrawl.url"
    FIRECRAWL_MODE = "skpl.firecrawl.mode"
    FIRECRAWL_STATUS_CODE = "skpl.firecrawl.status_code"
    FIRECRAWL_CONTENT_SIZE_BYTES = "skpl.firecrawl.content_size_bytes"
    FIRECRAWL_DURATION_MS = "skpl.firecrawl.duration_ms"

    # Code generation
    CODE_GEN_LANGUAGE = "skpl.code_gen.language"
    CODE_GEN_TASK = "skpl.code_gen.task"
    CODE_GEN_LINES_GENERATED = "skpl.code_gen.lines_generated"
    CODE_GEN_TOKENS_USED = "skpl.code_gen.tokens_used"
    CODE_GEN_DURATION_MS = "skpl.code_gen.duration_ms"

    # Common
    SESSION_ID = "skpl.session_id"
    AGENT_ID = "skpl.agent_id"


# ── Helper ───────────────────────────────────────────────────────────────────

def _now_ms() -> float:
    """Get the current time in milliseconds since epoch."""
    return time.time() * 1000


def _set_span_success(span: Span) -> None:
    """Mark a span as successful and end it."""
    span.set_status(StatusCode.OK)
    span.end()


def _set_span_error(span: Span, error: Exception) -> None:
    """Mark a span as failed, record the exception, and end it."""
    span.set_status(StatusCode.ERROR, str(error))
    span.record_exception(error)
    span.end()


# ── Span Context Managers ────────────────────────────────────────────────────


@contextmanager
def context_scan_span(
    session_id: str,
    root_path: str,
    scan_mode: str = "full",
    agent_id: Optional[str] = None,
) -> Generator[Span, None, None]:
    """Create a span for a context anatomy scan operation.

    Tracks the full lifecycle of a codebase scan: from initialization
    through file traversal and symbol extraction to completion.
    Records start/end timestamps, scan mode, and root path.

    Args:
        session_id: The session identifier for this scan.
        root_path: The root directory path being scanned.
        scan_mode: The scan mode ("full" or "incremental").
        agent_id: Optional agent identifier.

    Yields:
        An active OpenTelemetry Span that is automatically ended on exit.

    Example:
        with context_scan_span("sess-1", "/home/user/project", "full") as span:
            result = await scanner.scan()
            span.set_attribute(
                SKPLSpanAttributes.CONTEXT_SCAN_FILES_SCANNED,
                result.total_files_scanned,
            )
    """
    start_ms = _now_ms()
    attributes: dict[str, Any] = {
        SKPLSpanAttributes.CONTEXT_SCAN_ROOT_PATH: root_path,
        SKPLSpanAttributes.CONTEXT_SCAN_MODE: scan_mode,
        SKPLSpanAttributes.SESSION_ID: session_id,
    }
    if agent_id:
        attributes[SKPLSpanAttributes.AGENT_ID] = agent_id

    span = _tracer.start_span(
        name=f"context.scan {root_path}",
        kind=SpanKind.INTERNAL,
        attributes=attributes,
        start_time=int(start_ms * 1_000_000),  # nanoseconds
    )

    try:
        yield span
        end_ms = _now_ms()
        span.set_attribute(
            SKPLSpanAttributes.CONTEXT_SCAN_DURATION_SECONDS,
            (end_ms - start_ms) / 1000.0,
        )
        _set_span_success(span)
    except Exception as e:
        logger.error("Context scan span failed: %s", e)
        _set_span_error(span, e)
        raise


@contextmanager
def desktop_action_span(
    session_id: str,
    action_type: str,
    node_id: str,
    target: str = "",
    agent_id: Optional[str] = None,
) -> Generator[Span, None, None]:
    """Create a span for a desktop automation action.

    Tracks individual desktop actions (click, type, screenshot, etc.)
    executed through the Agent-S integration. Records the action type,
    target node, and timing information.

    Args:
        session_id: The session identifier.
        action_type: The type of desktop action (e.g., "click", "type", "screenshot").
        node_id: The identifier of the desktop node executing the action.
        target: Optional description of the action target (e.g., "button#submit").
        agent_id: Optional agent identifier.

    Yields:
        An active OpenTelemetry Span that is automatically ended on exit.

    Example:
        with desktop_action_span("sess-1", "click", "node-001", target="btn_ok") as span:
            result = await desktop_node.click(x=100, y=200)
            span.set_attribute("skpl.desktop.result", str(result))
    """
    start_ms = _now_ms()
    attributes: dict[str, Any] = {
        SKPLSpanAttributes.DESKTOP_ACTION_TYPE: action_type,
        SKPLSpanAttributes.DESKTOP_ACTION_NODE_ID: node_id,
        SKPLSpanAttributes.SESSION_ID: session_id,
    }
    if target:
        attributes[SKPLSpanAttributes.DESKTOP_ACTION_TARGET] = target
    if agent_id:
        attributes[SKPLSpanAttributes.AGENT_ID] = agent_id

    span = _tracer.start_span(
        name=f"desktop.{action_type}",
        kind=SpanKind.CLIENT,
        attributes=attributes,
        start_time=int(start_ms * 1_000_000),
    )

    try:
        yield span
        end_ms = _now_ms()
        span.set_attribute(
            SKPLSpanAttributes.DESKTOP_ACTION_DURATION_MS,
            end_ms - start_ms,
        )
        _set_span_success(span)
    except Exception as e:
        logger.error("Desktop action span failed: %s", e)
        _set_span_error(span, e)
        raise


@contextmanager
def firecrawl_request_span(
    session_id: str,
    url: str,
    mode: str = "scrape",
    agent_id: Optional[str] = None,
) -> Generator[Span, None, None]:
    """Create a span for a Firecrawl web scraping request.

    Tracks the lifecycle of a web scraping/crawling request through the
    Firecrawl integration. Records the target URL, crawl mode, HTTP status,
    and content size.

    Args:
        session_id: The session identifier.
        url: The target URL being scraped.
        mode: The crawl mode ("scrape", "crawl", "map").
        agent_id: Optional agent identifier.

    Yields:
        An active OpenTelemetry Span that is automatically ended on exit.

    Example:
        with firecrawl_request_span("sess-1", "https://example.com", "scrape") as span:
            result = await firecrawl.scrape(url)
            span.set_attribute(
                SKPLSpanAttributes.FIRECRAWL_CONTENT_SIZE_BYTES,
                len(result.content),
            )
    """
    start_ms = _now_ms()
    attributes: dict[str, Any] = {
        SKPLSpanAttributes.FIRECRAWL_URL: url,
        SKPLSpanAttributes.FIRECRAWL_MODE: mode,
        SKPLSpanAttributes.SESSION_ID: session_id,
    }
    if agent_id:
        attributes[SKPLSpanAttributes.AGENT_ID] = agent_id

    span = _tracer.start_span(
        name=f"firecrawl.{mode} {url}",
        kind=SpanKind.CLIENT,
        attributes=attributes,
        start_time=int(start_ms * 1_000_000),
    )

    try:
        yield span
        end_ms = _now_ms()
        span.set_attribute(
            SKPLSpanAttributes.FIRECRAWL_DURATION_MS,
            end_ms - start_ms,
        )
        _set_span_success(span)
    except Exception as e:
        logger.error("Firecrawl request span failed: %s", e)
        _set_span_error(span, e)
        raise


@contextmanager
def code_generation_span(
    session_id: str,
    language: str,
    task: str = "",
    agent_id: Optional[str] = None,
) -> Generator[Span, None, None]:
    """Create a span for a code generation operation.

    Tracks the lifecycle of an AI-assisted code generation request.
    Records the target language, task description, output metrics,
    and token usage.

    Args:
        session_id: The session identifier.
        language: The target programming language (e.g., "python", "typescript").
        task: A brief description of the generation task.
        agent_id: Optional agent identifier.

    Yields:
        An active OpenTelemetry Span that is automatically ended on exit.

    Example:
        with code_generation_span("sess-1", "python", "sort function") as span:
            code = await generate_code("sort function", language="python")
            span.set_attribute(
                SKPLSpanAttributes.CODE_GEN_LINES_GENERATED,
                len(code.splitlines()),
            )
    """
    start_ms = _now_ms()
    attributes: dict[str, Any] = {
        SKPLSpanAttributes.CODE_GEN_LANGUAGE: language,
        SKPLSpanAttributes.SESSION_ID: session_id,
    }
    if task:
        attributes[SKPLSpanAttributes.CODE_GEN_TASK] = task
    if agent_id:
        attributes[SKPLSpanAttributes.AGENT_ID] = agent_id

    span = _tracer.start_span(
        name=f"code_gen.{language}",
        kind=SpanKind.INTERNAL,
        attributes=attributes,
        start_time=int(start_ms * 1_000_000),
    )

    try:
        yield span
        end_ms = _now_ms()
        span.set_attribute(
            SKPLSpanAttributes.CODE_GEN_DURATION_MS,
            end_ms - start_ms,
        )
        _set_span_success(span)
    except Exception as e:
        logger.error("Code generation span failed: %s", e)
        _set_span_error(span, e)
        raise


__all__ = [
    "SKPLSpanAttributes",
    "context_scan_span",
    "desktop_action_span",
    "firecrawl_request_span",
    "code_generation_span",
]