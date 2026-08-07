"""SKPL Agent Multi-Model Engine (Agent-S Core Engine Integration).

Adapted from Agent-S gui_agents/s3/core/engine.py and mllm.py.
Provides a unified interface for multiple LLM backends with automatic
retry, rate limiting, and multimodal message management.

Supported backends:
    OpenAI, Anthropic, Azure OpenAI, Gemini, vLLM, OpenRouter, Ollama
"""

from skpl_agent.multi_model._engine import (
    LMEngine,
    OpenAIEngine,
    AnthropicEngine,
    AzureOpenAIEngine,
    create_engine,
)
from skpl_agent.multi_model._agent import (
    MultiModalAgent,
    Message,
    MessageRole,
)

__all__ = [
    # Engines
    "LMEngine",
    "OpenAIEngine",
    "AnthropicEngine",
    "AzureOpenAIEngine",
    "create_engine",
    # Agent
    "MultiModalAgent",
    "Message",
    "MessageRole",
]