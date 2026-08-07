"""Multi-modal agent for message management and engine routing.

Adapted from Agent-S gui_agents/s3/core/mllm.py.
Manages conversation history, system prompts, and multimodel
message routing with image support.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from skpl_agent.multi_model._engine import LMEngine, EngineConfig, create_engine

logger = logging.getLogger(__name__)


class MessageRole(str, Enum):
    """Standard message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """A single message in a conversation."""

    role: str
    content: str
    images: list[str] = field(default_factory=list)  # base64-encoded


class MultiModalAgent:
    """Multi-modal agent for conversation management.

    Handles:
    - System prompt management
    - Message history with image support
    - Engine routing and response generation
    - Context window management

    Usage:
        >>> agent = MultiModalAgent(
        ...     engine_type="openai",
        ...     system_prompt="You are a helpful assistant.",
        ...     engine_config=EngineConfig(model="gpt-4o"),
        ... )
        >>> agent.add_message("What is in this image?", images=["base64..."])
        >>> response = await agent.get_response()
    """

    def __init__(
        self,
        engine_type: str = "openai",
        system_prompt: str | None = None,
        engine_config: EngineConfig | None = None,
    ) -> None:
        self._engine = create_engine(
            engine_type,
            engine_config or EngineConfig(model="gpt-4o"),
        )
        self._messages: list[Message] = []
        self._system_prompt = system_prompt

    # ── Message management ───────────────────────────────────────────────

    def add_message(
        self,
        text: str,
        images: list[str] | None = None,
        role: str = "user",
    ) -> None:
        """Add a message to the conversation history.

        Args:
            text: The text content.
            images: Optional list of base64-encoded images.
            role: Message role (user, assistant, system).
        """
        self._messages.append(
            Message(role=role, content=text, images=images or [])
        )

    def add_system_prompt(self, prompt: str) -> None:
        """Set or replace the system prompt."""
        self._system_prompt = prompt

    def reset(self) -> None:
        """Clear all messages (keeps system prompt)."""
        self._messages.clear()

    # ── Response generation ──────────────────────────────────────────────

    async def get_response(
        self,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate a response from the LLM.

        Automatically builds the message list with system prompt and
        multimodal content (text + images).

        Args:
            temperature: Sampling temperature.
            max_tokens: Max tokens in response.
            **kwargs: Additional engine-specific parameters.

        Returns:
            The generated text response.
        """
        api_messages = self._build_api_messages()
        response = await self._engine.generate(
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return response

    def _build_api_messages(self) -> list[dict[str, Any]]:
        """Build the API-compatible message list."""
        api_messages: list[dict[str, Any]] = []

        # System prompt
        if self._system_prompt:
            api_messages.append({
                "role": "system",
                "content": self._system_prompt,
            })

        # Conversation messages
        for msg in self._messages:
            if msg.images:
                # Multimodal content
                content_parts: list[dict[str, Any]] = [
                    {"type": "text", "text": msg.content},
                ]
                for img in msg.images:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img}"},
                    })
                api_messages.append({
                    "role": msg.role,
                    "content": content_parts,
                })
            else:
                api_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        return api_messages

    # ── Image utilities ───────────────────────────────────────────────────

    @staticmethod
    def encode_image(image_path: str) -> str:
        """Encode an image file to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def encode_image_bytes(image_bytes: bytes) -> str:
        """Encode image bytes to base64."""
        return base64.b64encode(image_bytes).decode("utf-8")

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def message_count(self) -> int:
        """Number of messages in history."""
        return len(self._messages)

    @property
    def engine(self) -> LMEngine:
        """The underlying LLM engine."""
        return self._engine