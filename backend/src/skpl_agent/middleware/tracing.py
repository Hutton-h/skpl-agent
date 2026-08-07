"""OpenTelemetry tracing middleware — distributed tracing for ASGI applications.

Provides automatic span creation for HTTP requests, agent invocations,
tool calls, and context operations. Integrates with the OpenTelemetry SDK
for export to Jaeger, Zipkin, OTLP collectors, etc.

Architecture:
    ┌─ Request ─► TracingMiddleware ─► App
    │                  │
    │           ┌──────┴──────┐
    │           ▼              ▼
    │     HTTP Span       Agent Span
    │           │              │
    │           └──────┬──────┘
    │                  ▼
    │           OTLP Exporter
    │                  │
    │           ┌──────┴──────┐
    │           ▼              ▼
    │       Jaeger         Prometheus
"""

from __future__ import annotations

import contextvars
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import (
    Span,
    SpanKind,
    StatusCode,
    Tracer,
    get_tracer,
    set_tracer_provider,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Context variable for the "current" span, so nested operations can adopt it
_current_span: contextvars.ContextVar[Span | None] = contextvars.ContextVar(
    "skpl_current_span", default=None
)


# ---------------------------------------------------------------------------
# Tracer Setup
# ---------------------------------------------------------------------------


def setup_tracing(
    service_name: str = "skpl-agent",
    service_version: str = "0.1.0",
    environment: str = "development",
    exporter_endpoint: str | None = None,
    sample_rate: float = 1.0,
) -> Tracer:
    """Initialize OpenTelemetry tracing with the OTLP exporter.

    Args:
        service_name: Name of the service in traces.
        service_version: Service version tag.
        environment: Deployment environment (development, staging, production).
        exporter_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317").
                            If None, uses a no-op exporter.
        sample_rate: Fraction of traces to sample (0.0 - 1.0).

    Returns:
        A configured Tracer instance.
    """
    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
        "deployment.environment": environment,
    })

    provider = TracerProvider(resource=resource)

    if exporter_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            exporter = OTLPSpanExporter(endpoint=exporter_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info(
                "OTLP tracing exporter configured [endpoint=%s]", exporter_endpoint,
            )
        except ImportError:
            logger.warning(
                "opentelemetry-exporter-otlp not installed — tracing is no-op",
            )

    set_tracer_provider(provider)
    tracer = get_tracer(service_name, service_version)

    logger.info(
        "Tracing initialized [service=%s, version=%s, env=%s, rate=%.2f]",
        service_name, service_version, environment, sample_rate,
    )
    return tracer


# ---------------------------------------------------------------------------
# Tracing Middleware
# ---------------------------------------------------------------------------


class TracingMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that creates OpenTelemetry spans for each HTTP request.

    Each span captures:
    - HTTP method, URL, status code
    - Request duration
    - User agent and client IP
    - Error details (if any)
    """

    def __init__(
        self,
        app,
        *,
        tracer: Tracer | None = None,
        service_name: str = "skpl-agent",
        include_request_body: bool = False,
        include_response_body: bool = False,
        max_body_length: int = 4096,
    ) -> None:
        super().__init__(app)
        self._tracer = tracer or get_tracer(service_name)
        self._include_request_body = include_request_body
        self._include_response_body = include_response_body
        self._max_body_length = max_body_length

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip tracing for health/readiness endpoints
        if self._is_skippable(request.url.path):
            return await call_next(request)

        span_name = f"{request.method} {request.url.path}"
        with self._tracer.start_as_current_span(
            span_name,
            kind=SpanKind.SERVER,
            attributes=self._extract_request_attributes(request),
        ) as span:
            _current_span.set(span)

            start_time = time.monotonic()
            status_code = 500
            response: Response | None = None

            try:
                response = await call_next(request)
                status_code = response.status_code
                span.set_status(StatusCode.OK)
                return response
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(StatusCode.ERROR, str(exc))
                raise
            finally:
                duration_ms = (time.monotonic() - start_time) * 1000
                span.set_attribute(SpanAttributes.HTTP_STATUS_CODE, status_code)
                span.set_attribute("http.duration_ms", duration_ms)

                if response is not None and self._include_response_body:
                    try:
                        body = response.body[:self._max_body_length]
                        span.set_attribute("http.response.body_sample", body.decode("utf-8", errors="replace"))
                    except Exception:
                        pass

    # ---- Helpers ----

    @staticmethod
    def _is_skippable(path: str) -> bool:
        skippable = {"/health", "/metrics", "/ready", "/livez", "/healthz"}
        return path in skippable or path.startswith("/static/")

    def _extract_request_attributes(self, request: Request) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            SpanAttributes.HTTP_METHOD: request.method,
            SpanAttributes.HTTP_URL: str(request.url),
            SpanAttributes.HTTP_SCHEME: request.url.scheme,
            SpanAttributes.HTTP_TARGET: request.url.path,
            SpanAttributes.NET_HOST_NAME: request.url.hostname or "",
            SpanAttributes.NET_HOST_PORT: request.url.port or 0,
            SpanAttributes.USER_AGENT_ORIGINAL: request.headers.get("User-Agent", ""),
            "http.client_ip": self._get_client_ip(request),
        }
        if self._include_request_body and request.method in ("POST", "PUT", "PATCH"):
            try:
                # Read body without consuming (works for small bodies)
                body = request.headers.get("content-length", "0")
                attrs["http.request.content_length"] = body
            except Exception:
                pass
        return attrs

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# Span Utilities
# ---------------------------------------------------------------------------


def get_current_span() -> Span | None:
    """Get the currently active OpenTelemetry span (if any)."""
    span = _current_span.get()
    if span is not None:
        return span
    return trace.get_current_span()


@asynccontextmanager
async def traced_agent_invocation(
    agent_id: str,
    session_id: str,
    model_name: str | None = None,
    tracer: Tracer | None = None,
) -> AsyncIterator[Span]:
    """Create a span for an agent invocation and track its duration.

    Usage:
        async with traced_agent_invocation("agent-1", "session-abc") as span:
            result = await agent.run(prompt)
            span.set_attribute("agent.output_tokens", result.usage.output_tokens)
    """
    _tracer = tracer or get_tracer("skpl-agent")
    with _tracer.start_as_current_span(
        "agent.invoke",
        kind=SpanKind.INTERNAL,
        attributes={
            "agent.id": agent_id,
            "session.id": session_id,
            "agent.model": model_name or "unknown",
        },
    ) as span:
        _current_span.set(span)
        start = time.monotonic()
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(StatusCode.ERROR, str(exc))
            raise
        finally:
            span.set_attribute("agent.duration_ms", (time.monotonic() - start) * 1000)


@asynccontextmanager
async def traced_tool_call(
    tool_name: str,
    tool_args: dict[str, Any] | None = None,
    tracer: Tracer | None = None,
) -> AsyncIterator[Span]:
    """Create a span for a tool invocation.

    Usage:
        async with traced_tool_call("firecrawl.scrape", {"url": "..."}) as span:
            result = await firecrawl.scrape(url)
            span.set_attribute("tool.result_length", len(result))
    """
    _tracer = tracer or get_tracer("skpl-agent")
    attrs: dict[str, Any] = {"tool.name": tool_name}
    if tool_args:
        attrs["tool.args"] = str(tool_args)[:1024]
    with _tracer.start_as_current_span(
        f"tool.{tool_name}",
        kind=SpanKind.INTERNAL,
        attributes=attrs,
    ) as span:
        _current_span.set(span)
        start = time.monotonic()
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(StatusCode.ERROR, str(exc))
            raise
        finally:
            span.set_attribute("tool.duration_ms", (time.monotonic() - start) * 1000)


@asynccontextmanager
async def traced_context_operation(
    operation: str,
    session_id: str,
    tracer: Tracer | None = None,
) -> AsyncIterator[Span]:
    """Create a span for a context management operation.

    Usage:
        async with traced_context_operation("anatomy.scan", "session-abc") as span:
            result = await scanner.scan(project_root)
            span.set_attribute("context.symbols_found", len(result.symbols))
    """
    _tracer = tracer or get_tracer("skpl-agent")
    with _tracer.start_as_current_span(
        f"context.{operation}",
        kind=SpanKind.INTERNAL,
        attributes={
            "context.operation": operation,
            "session.id": session_id,
        },
    ) as span:
        _current_span.set(span)
        start = time.monotonic()
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(StatusCode.ERROR, str(exc))
            raise
        finally:
            span.set_attribute("context.duration_ms", (time.monotonic() - start) * 1000)


__all__ = [
    "TracingMiddleware",
    "setup_tracing",
    "get_current_span",
    "traced_agent_invocation",
    "traced_tool_call",
    "traced_context_operation",
]