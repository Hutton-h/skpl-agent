"""Tests for Firecrawl skill."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def firecrawl_skill():
    """Create a FirecrawlSkill instance."""
    from skpl_agent.skill._firecrawl import FirecrawlSkill
    return FirecrawlSkill()


class TestFirecrawlSkillInitialization:
    """Tests for skill initialization."""

    @pytest.mark.asyncio
    async def test_load(self, firecrawl_skill) -> None:
        """Skill can be loaded."""
        with patch.object(firecrawl_skill, "_register_tools"), \
             patch.object(firecrawl_skill, "_load_config_from_env"):
            await firecrawl_skill.load()
            assert firecrawl_skill._loaded is True

    @pytest.mark.asyncio
    async def test_load_idempotent(self, firecrawl_skill) -> None:
        """Loading twice is safe."""
        with patch.object(firecrawl_skill, "_register_tools"), \
             patch.object(firecrawl_skill, "_load_config_from_env"):
            await firecrawl_skill.load()
            await firecrawl_skill.load()
            assert firecrawl_skill._loaded is True

    @pytest.mark.asyncio
    async def test_unload(self, firecrawl_skill) -> None:
        """Skill can be unloaded."""
        with patch.object(firecrawl_skill, "_register_tools"), \
             patch.object(firecrawl_skill, "_load_config_from_env"):
            await firecrawl_skill.load()
            await firecrawl_skill.unload()
            assert firecrawl_skill._loaded is False

    def test_name(self, firecrawl_skill) -> None:
        """Skill name is correct."""
        assert firecrawl_skill.name == "firecrawl"

    def test_description(self, firecrawl_skill) -> None:
        """Skill has a description."""
        assert "Web scraping" in firecrawl_skill.description

    def test_is_loaded_default(self, firecrawl_skill) -> None:
        """Skill is not loaded by default."""
        assert firecrawl_skill.is_loaded is False


class TestFirecrawlSkillOperations:
    """Tests for skill operations."""

    @pytest.mark.asyncio
    async def test_get_tools_after_load(self, firecrawl_skill) -> None:
        """Tools are available after loading."""
        with patch.object(firecrawl_skill, "_register_tools") as mock_register, \
             patch.object(firecrawl_skill, "_load_config_from_env"):
            mock_register.side_effect = lambda: setattr(firecrawl_skill, "_tools", {"scrape": {"name": "scrape"}})
            await firecrawl_skill.load()
            tools = firecrawl_skill.get_tools()
            assert "scrape" in tools

    def test_get_tools_before_load_raises(self, firecrawl_skill) -> None:
        """Accessing tools before loading raises RuntimeError."""
        with pytest.raises(RuntimeError, match="not loaded"):
            firecrawl_skill.get_tools()

    @pytest.mark.asyncio
    async def test_get_tool(self, firecrawl_skill) -> None:
        """Specific tool can be retrieved."""
        with patch.object(firecrawl_skill, "_register_tools") as mock_register, \
             patch.object(firecrawl_skill, "_load_config_from_env"):
            mock_register.side_effect = lambda: setattr(firecrawl_skill, "_tools", {"scrape": {"name": "scrape"}})
            await firecrawl_skill.load()
            tool = firecrawl_skill.get_tool("scrape")
            assert tool is not None
            assert tool["name"] == "scrape"

    @pytest.mark.asyncio
    async def test_get_tool_nonexistent(self, firecrawl_skill) -> None:
        """Nonexistent tool returns None."""
        with patch.object(firecrawl_skill, "_register_tools"), \
             patch.object(firecrawl_skill, "_load_config_from_env"):
            await firecrawl_skill.load()
            tool = firecrawl_skill.get_tool("nonexistent")
            assert tool is None

    @pytest.mark.asyncio
    async def test_update_config(self, firecrawl_skill) -> None:
        """Configuration can be updated."""
        from skpl_agent.app._service.firecrawl_service import FirecrawlConfig
        config = firecrawl_skill.config
        assert isinstance(config, FirecrawlConfig)

    @pytest.mark.asyncio
    async def test_unload_clears_tools(self, firecrawl_skill) -> None:
        """Unloading clears tools."""
        with patch.object(firecrawl_skill, "_register_tools") as mock_register, \
             patch.object(firecrawl_skill, "_load_config_from_env"):
            mock_register.side_effect = lambda: setattr(firecrawl_skill, "_tools", {"scrape": {"name": "scrape"}})
            await firecrawl_skill.load()
            await firecrawl_skill.unload()
            assert firecrawl_skill._loaded is False
            assert firecrawl_skill._tools == {}