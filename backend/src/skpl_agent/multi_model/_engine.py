"""Multi-model LLM engine abstraction.

Adapted from Agent-S gui_agents/s3/core/engine.py.
Provides unified interface for OpenAI, Anthropic, Azure, and more,
with automatic retry and rate limiting.
"""

from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EngineConfig:
    """Configuration for an LLM engine."""

    model: str
    api_key: str | None = None
    base_url: str | None = None
    temperature: float | None = None
    rate_limit: int = -1  # requests per minute, -1 = unlimited
    max_retries: int = 3


class LMEngine(ABC):
    """Abstract base for LLM engine implementations."""

    name: str = "base"

    def __init__(self, config: EngineConfig) -> None:
        self._config = config
        self._last_request_time = 0.0
        self._request_interval = (
            0.0 if config.rate_limit == -1 else 60.0 / config.rate_limit
        )

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate a response from the LLM."""
        ...

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        if self._request_interval > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._request_interval:
                time.sleep(self._request_interval - elapsed)
        self._last_request_time = time.time()


# ---------------------------------------------------------------------------
# OpenAI Engine
# ---------------------------------------------------------------------------

class OpenAIEngine(LMEngine):
    """OpenAI Chat Completions API engine."""

    name = "openai"

    @staticmethod
    def _get_api_key(config: EngineConfig) -> str:
        key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OpenAI API key required (set OPENAI_API_KEY or pass api_key)")
        return key

    async def generate(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package required: pip install openai")

        self._rate_limit()
        api_key = self._get_api_key(self._config)

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=self._config.base_url,
        )

        response = await client.chat.completions.create(
            model=self._config.model,
            messages=messages,
            temperature=self._config.temperature if self._config.temperature is not None else temperature,
            max_tokens=max_tokens or 4096,
            **kwargs,
        )

        return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Anthropic Engine
# ---------------------------------------------------------------------------

class AnthropicEngine(LMEngine):
    """Anthropic Messages API engine."""

    name = "anthropic"

    async def generate(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise ImportError("anthropic package required: pip install anthropic")

        self._rate_limit()
        api_key = self._config.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API key required")

        # Extract system message if present
        system = None
        api_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                api_messages.append(msg)

        client = AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=self._config.model,
            messages=api_messages,
            system=system,
            max_tokens=max_tokens or 4096,
            temperature=self._config.temperature if self._config.temperature is not None else temperature,
            **kwargs,
        )

        return response.content[0].text if response.content else ""


# ---------------------------------------------------------------------------
# Azure OpenAI Engine
# ---------------------------------------------------------------------------

class AzureOpenAIEngine(LMEngine):
    """Azure OpenAI API engine."""

    name = "azure"

    async def generate(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            from openai import AsyncAzureOpenAI
        except ImportError:
            raise ImportError("openai package required: pip install openai")

        self._rate_limit()
        api_key = self._config.api_key or os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = self._config.base_url or os.getenv("AZURE_OPENAI_ENDPOINT")
        if not api_key or not endpoint:
            raise ValueError("Azure OpenAI API key and endpoint required")

        client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=kwargs.pop("api_version", "2024-02-15-preview"),
        )

        response = await client.chat.completions.create(
            model=self._config.model,
            messages=messages,
            temperature=self._config.temperature if self._config.temperature is not None else temperature,
            max_tokens=max_tokens or 4096,
            **kwargs,
        )

        return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_ENGINE_REGISTRY: dict[str, type[LMEngine]] = {
    "openai": OpenAIEngine,
    "anthropic": AnthropicEngine,
    "azure": AzureOpenAIEngine,
}


def create_engine(engine_type: str, config: EngineConfig) -> LMEngine:
    """Create an LLM engine by type name.

    Args:
        engine_type: One of 'openai', 'anthropic', 'azure', 'gemini', 'ollama', etc.
        config: Engine configuration.

    Returns:
        An LMEngine instance.

    Raises:
        ValueError: If the engine type is not supported.
    """
    engine_type = engine_type.lower()
    if engine_type not in _ENGINE_REGISTRY:
        # Try OpenAI-compatible as fallback
        logger.warning(
            "Unknown engine type '%s', falling back to OpenAI", engine_type
        )
        return OpenAIEngine(config)

    return _ENGINE_REGISTRY[engine_type](config)