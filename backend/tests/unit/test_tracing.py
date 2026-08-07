"""Tests for tracing middleware."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from skpl_agent.middleware.tracing import (
    TracingMiddleware,
    get_current_span,
    setup_tracing,
    traced_agent_invocation,
    traced_context_operation,
    traced_tool_call,
)


class TestTracingSetup:
    """Tests for tracing setup."""

    def test_setup_tracing_defaults(self) -> None:
        """setup_tracing works with defaults."""
        tracer = setup_tracing()
        assert tracer is not None

    def test_setup_tracing_custom_name(self) -> None:
        """setup_tracing accepts custom service name."""
        tracer = setup_tracing(
            service_name="test-service",
            service_version="2.0.0",
            environment="testing",
        )
        assert tracer is not None

    def test_setup_tracing_without_exporter(self) -> None:
        """setup_tracing works without OTLP exporter."""
        tracer = setup_tracing(exporter_endpoint=None)
        assert tracer is not None


class TestTracingMiddleware:
    """Integration tests for TracingMiddleware."""

    @pytest.fixture
    def app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        @app.get("/api/test")
        async def test():
            return {"data": "test"}

        @app.get("/api/error")
        async def error_endpoint():
            raise ValueError("test error")

        app.add_middleware(TracingMiddleware)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        return TestClient(app)

    def test_health_skipped(self, client: TestClient) -> None:
        """Health endpoint is not traced."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_normal_request(self, client: TestClient) -> None:
        """Normal requests are traced without error."""
        response = client.get("/api/test")
        assert response.status_code == 200
        assert response.json() == {"data": "test"}

    def test_error_request(self, client: TestClient) -> None:
        """Error requests are traced with exception."""
        response = client.get("/api/error")
        assert response.status_code == 500

    def test_metrics_endpoint_skipped(self, client: TestClient) -> None:
        """Metrics endpoint is not traced."""
        response = client.get("/metrics")
        assert response.status_code == 200


class TestSpanUtilities:
    """Tests for span utility functions."""

    def test_get_current_span_no_span(self) -> None:
        """get_current_span returns None when no span is active."""
        span = get_current_span()
        # May return a non-recording span or None
        if span is not None:
            assert not span.is_recording()

    @pytest.mark.asyncio
    async def test_traced_agent_invocation(self) -> None:
        """traced_agent_invocation creates a span."""
        async with traced_agent_invocation(
            agent_id="agent-1",
            session_id="session-abc",
            model_name="gpt-4",
        ) as span:
            span.set_attribute("agent.output_tokens", 150)

    @pytest.mark.asyncio
    async def test_traced_agent_error(self) -> None:
        """traced_agent_invocation records exceptions."""
        with pytest.raises(ValueError, match="test error"):
            async with traced_agent_invocation(
                agent_id="agent-1",
                session_id="session-abc",
            ):
                raise ValueError("test error")

    @pytest.mark.asyncio
    async def test_traced_tool_call(self) -> None:
        """traced_tool_call creates a span."""
        async with traced_tool_call(
            tool_name="firecrawl.scrape",
            tool_args={"url": "https://example.com"},
        ) as span:
            span.set_attribute("tool.result_length", 1024)

    @pytest.mark.asyncio
    async def test_traced_context_operation(self) -> None:
        """traced_context_operation creates a span."""
        async with traced_context_operation(
            operation="anatomy.scan",
            session_id="session-abc",
        ) as span:
            span.set_attribute("context.symbols_found", 42)