"""SKPL Agent Middleware.

Provides ASGI middleware components for the FastAPI application:
- RateLimitMiddleware: Token Bucket rate limiting per IP and API key
- TracingMiddleware: OpenTelemetry distributed tracing for HTTP requests
- ContextMiddleware: OpenWolf context lifecycle hooks injection
"""

from skpl_agent.middleware._base import MiddlewareBase
from skpl_agent.middleware._rag import RAGMiddleware
from skpl_agent.middleware._tts_middleware import TTSMiddleware
from skpl_agent.middleware.context_middleware import ContextMiddleware
from skpl_agent.middleware.rate_limit import (
    RateLimitConfig,
    RateLimitMiddleware,
    TokenBucket,
    create_rate_limit_middleware,
)
from skpl_agent.middleware.token_middleware import TokenMiddleware
from skpl_agent.middleware.tracing import (
    TracingMiddleware,
    get_current_span,
    setup_tracing,
    traced_agent_invocation,
    traced_context_operation,
    traced_tool_call,
)

__all__ = [
    # Base
    "MiddlewareBase",
    # RAG
    "RAGMiddleware",
    # TTS
    "TTSMiddleware",
    # Token
    "TokenMiddleware",
    # Rate limiting
    "RateLimitMiddleware",
    "RateLimitConfig",
    "TokenBucket",
    "create_rate_limit_middleware",
    # Tracing
    "TracingMiddleware",
    "setup_tracing",
    "get_current_span",
    "traced_agent_invocation",
    "traced_tool_call",
    "traced_context_operation",
    # Context
    "ContextMiddleware",
]