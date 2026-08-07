"""Unit tests for config.py — Pydantic Settings configuration classes.

Tests cover:
- CoreSettings, ContextSettings, DesktopSettings, WebSettings,
  UpdateSettings, QuotaSettings, and the unified Settings class.
- Default values, environment variable overrides, field validators,
  and list parsing from comma-separated strings.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError

from skpl_agent.config import (
    CoreSettings,
    ContextSettings,
    DesktopSettings,
    QuotaSettings,
    Settings,
    UpdateSettings,
    WebSettings,
    get_settings,
)


# ── CoreSettings Tests ────────────────────────────────────────────────────


class TestCoreSettings:
    """Tests for CoreSettings (prefix: SKPL_CORE_)."""

    def test_default_values(self) -> None:
        """CoreSettings initializes with sensible defaults."""
        cfg = CoreSettings()
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 8000
        assert cfg.workers == 1
        assert cfg.debug is False
        assert cfg.database_url == "sqlite+aiosqlite:///data/skpl.db"
        assert cfg.database_echo is False
        assert cfg.redis_url is None
        assert cfg.log_level == "INFO"
        assert cfg.log_format == "json"
        assert isinstance(cfg.log_dir, Path)
        assert cfg.cors_origins == ["http://localhost:5173"]
        assert isinstance(cfg.data_dir, Path)

    def test_secret_key_is_secret_str(self) -> None:
        """secret_key is a SecretStr for security."""
        cfg = CoreSettings()
        assert isinstance(cfg.secret_key, SecretStr)
        assert cfg.secret_key.get_secret_value() == "change-me-in-production"

    def test_environment_variable_override(self) -> None:
        """Environment variables with SKPL_CORE_ prefix override defaults."""
        with patch.dict(os.environ, {
            "SKPL_CORE_HOST": "127.0.0.1",
            "SKPL_CORE_PORT": "9090",
            "SKPL_CORE_DEBUG": "true",
            "SKPL_CORE_LOG_LEVEL": "DEBUG",
            "SKPL_CORE_LOG_FORMAT": "console",
            "SKPL_CORE_DATABASE_URL": "postgresql://localhost/test",
            "SKPL_CORE_REDIS_URL": "redis://localhost:6379",
            "SKPL_CORE_WORKERS": "4",
            "SKPL_CORE_DATABASE_ECHO": "true",
        }):
            cfg = CoreSettings()
            assert cfg.host == "127.0.0.1"
            assert cfg.port == 9090
            assert cfg.debug is True
            assert cfg.log_level == "DEBUG"
            assert cfg.log_format == "console"
            assert cfg.database_url == "postgresql://localhost/test"
            assert cfg.redis_url == "redis://localhost:6379"
            assert cfg.workers == 4
            assert cfg.database_echo is True

    def test_cors_origins_from_string(self) -> None:
        """cors_origins parses JSON array string."""
        with patch.dict(os.environ, {
            "SKPL_CORE_CORS_ORIGINS": '["http://a.com", "http://b.com", "http://c.com"]',
        }):
            cfg = CoreSettings()
            assert cfg.cors_origins == ["http://a.com", "http://b.com", "http://c.com"]

    def test_cors_origins_single_value(self) -> None:
        """cors_origins handles single string value."""
        with patch.dict(os.environ, {
            "SKPL_CORE_CORS_ORIGINS": '["http://single.com"]',
        }):
            cfg = CoreSettings()
            assert cfg.cors_origins == ["http://single.com"]

    def test_log_level_invalid_raises(self) -> None:
        """Invalid log_level raises ValidationError."""
        with patch.dict(os.environ, {"SKPL_CORE_LOG_LEVEL": "TRACE"}):
            with pytest.raises(ValidationError):
                CoreSettings()

    def test_log_format_invalid_raises(self) -> None:
        """Invalid log_format raises ValidationError."""
        with patch.dict(os.environ, {"SKPL_CORE_LOG_FORMAT": "xml"}):
            with pytest.raises(ValidationError):
                CoreSettings()


# ── ContextSettings Tests ─────────────────────────────────────────────────


class TestContextSettings:
    """Tests for ContextSettings (prefix: SKPL_CONTEXT_)."""

    def test_default_values(self) -> None:
        """ContextSettings has sensible defaults."""
        cfg = ContextSettings()
        assert cfg.anatomy_use_json is False
        assert cfg.scan_max_file_size_mb == 5
        assert cfg.scan_interval_seconds == 300
        assert cfg.scan_parallel_workers == 4
        assert cfg.token_budget == 200000
        assert cfg.token_waste_threshold == 0.30
        assert cfg.token_ledger_flush_interval == 60
        assert cfg.buglog_jaccard_threshold == 0.75
        assert cfg.buglog_max_entries == 10000

    def test_scan_include_patterns_default(self) -> None:
        """scan_include_patterns covers common source file types."""
        cfg = ContextSettings()
        assert "**/*.py" in cfg.scan_include_patterns
        assert "**/*.ts" in cfg.scan_include_patterns
        assert "**/*.go" in cfg.scan_include_patterns
        assert "**/*.rs" in cfg.scan_include_patterns

    def test_scan_exclude_patterns_default(self) -> None:
        """scan_exclude_patterns excludes build artifacts."""
        cfg = ContextSettings()
        assert "**/node_modules/**" in cfg.scan_exclude_patterns
        assert "**/__pycache__/**" in cfg.scan_exclude_patterns
        assert "**/.git/**" in cfg.scan_exclude_patterns
        assert "**/dist/**" in cfg.scan_exclude_patterns

    def test_sensitive_patterns_default(self) -> None:
        """sensitive_patterns includes API key and password patterns."""
        cfg = ContextSettings()
        assert len(cfg.sensitive_patterns) >= 3
        # Check that at least one pattern covers API keys
        assert any("api" in p.lower() for p in cfg.sensitive_patterns)

    def test_sensitive_file_patterns_default(self) -> None:
        """sensitive_file_patterns covers .env and credential files."""
        cfg = ContextSettings()
        assert "**/.env" in cfg.sensitive_file_patterns
        assert "**/.env.*" in cfg.sensitive_file_patterns

    def test_environment_variable_override(self) -> None:
        """SKPL_CONTEXT_ vars override defaults."""
        with patch.dict(os.environ, {
            "SKPL_CONTEXT_TOKEN_BUDGET": "500000",
            "SKPL_CONTEXT_SCAN_MAX_FILE_SIZE_MB": "10",
            "SKPL_CONTEXT_SCAN_INTERVAL_SECONDS": "600",
            "SKPL_CONTEXT_BUGLOG_JACCARD_THRESHOLD": "0.85",
        }):
            cfg = ContextSettings()
            assert cfg.token_budget == 500000
            assert cfg.scan_max_file_size_mb == 10
            assert cfg.scan_interval_seconds == 600
            assert cfg.buglog_jaccard_threshold == 0.85

    def test_list_fields_from_comma_string(self) -> None:
        """List fields parse JSON array strings."""
        with patch.dict(os.environ, {
            "SKPL_CONTEXT_SCAN_INCLUDE_PATTERNS": '["*.py", "*.rs", "*.go"]',
            "SKPL_CONTEXT_SENSITIVE_FILE_PATTERNS": '[".env", ".secrets"]',
        }):
            cfg = ContextSettings()
            assert cfg.scan_include_patterns == ["*.py", "*.rs", "*.go"]
            assert cfg.sensitive_file_patterns == [".env", ".secrets"]

    def test_anatomy_store_path_default(self) -> None:
        """anatomy_store_path defaults to a .db path under data dir."""
        cfg = ContextSettings()
        assert cfg.anatomy_store_path.name == "anatomy_store.db"


# ── DesktopSettings Tests ─────────────────────────────────────────────────


class TestDesktopSettings:
    """Tests for DesktopSettings (prefix: SKPL_DESKTOP_)."""

    def test_default_values(self) -> None:
        """DesktopSettings has sensible defaults."""
        cfg = DesktopSettings()
        assert cfg.ws_host == "0.0.0.0"
        assert cfg.ws_port == 8001
        assert cfg.ws_heartbeat_interval == 10
        assert cfg.ws_reconnect_backoff_base == 1.0
        assert cfg.ws_reconnect_backoff_max == 60.0
        assert cfg.ws_token_expiry == 3600
        assert cfg.node_max_offline_seconds == 60
        assert cfg.node_cleanup_interval == 30
        assert cfg.desktop_rate_limit_per_minute == 60
        assert cfg.desktop_rate_limit_burst == 10
        assert cfg.action_timeout_seconds == 30
        assert cfg.screenshot_timeout_seconds == 10
        assert cfg.ocr_timeout_seconds == 30
        assert cfg.grounding_model == "microsoft/OmniParser-v2"
        assert cfg.grounding_device == "cpu"
        assert cfg.ocr_enabled is True
        assert cfg.ocr_lang == "ch"

    def test_environment_variable_override(self) -> None:
        """SKPL_DESKTOP_ vars override defaults."""
        with patch.dict(os.environ, {
            "SKPL_DESKTOP_WS_PORT": "9001",
            "SKPL_DESKTOP_WS_HEARTBEAT_INTERVAL": "30",
            "SKPL_DESKTOP_OCR_ENABLED": "false",
            "SKPL_DESKTOP_GROUNDING_DEVICE": "cuda",
            "SKPL_DESKTOP_DESKTOP_RATE_LIMIT_PER_MINUTE": "120",
        }):
            cfg = DesktopSettings()
            assert cfg.ws_port == 9001
            assert cfg.ws_heartbeat_interval == 30
            assert cfg.ocr_enabled is False
            assert cfg.grounding_device == "cuda"
            assert cfg.desktop_rate_limit_per_minute == 120

    def test_grounding_device_invalid_raises(self) -> None:
        """Invalid grounding_device raises ValidationError."""
        with patch.dict(os.environ, {"SKPL_DESKTOP_GROUNDING_DEVICE": "tpu"}):
            with pytest.raises(ValidationError):
                DesktopSettings()


# ── WebSettings Tests ─────────────────────────────────────────────────────


class TestWebSettings:
    """Tests for WebSettings (prefix: SKPL_WEB_)."""

    def test_default_values(self) -> None:
        """WebSettings has sensible defaults."""
        cfg = WebSettings()
        assert cfg.crawler_timeout == 30
        assert cfg.crawler_max_redirects == 5
        assert cfg.crawler_concurrency == 3
        assert cfg.crawler_delay == 1.0
        assert cfg.ssrf_enabled is True
        assert cfg.ssrf_block_localhost is True
        assert cfg.ssrf_dns_rebinding_protection is True
        assert cfg.content_max_size_mb == 50
        assert "markdown" in cfg.content_formats
        assert "html" in cfg.content_formats
        assert cfg.web_rate_limit_per_minute == 30

    def test_ssrf_blocked_networks_default(self) -> None:
        """ssrf_blocked_networks includes private IP ranges."""
        cfg = WebSettings()
        assert "10.0.0.0/8" in cfg.ssrf_blocked_networks
        assert "192.168.0.0/16" in cfg.ssrf_blocked_networks
        assert "127.0.0.0/8" in cfg.ssrf_blocked_networks

    def test_environment_variable_override(self) -> None:
        """SKPL_WEB_ vars override defaults."""
        with patch.dict(os.environ, {
            "SKPL_WEB_CRAWLER_TIMEOUT": "60",
            "SKPL_WEB_CRAWLER_CONCURRENCY": "5",
            "SKPL_WEB_SSRF_ENABLED": "false",
            "SKPL_WEB_CONTENT_MAX_SIZE_MB": "100",
            "SKPL_WEB_WEB_RATE_LIMIT_PER_MINUTE": "60",
        }):
            cfg = WebSettings()
            assert cfg.crawler_timeout == 60
            assert cfg.crawler_concurrency == 5
            assert cfg.ssrf_enabled is False
            assert cfg.content_max_size_mb == 100
            assert cfg.web_rate_limit_per_minute == 60

    def test_content_formats_from_string(self) -> None:
        """content_formats parses JSON array string."""
        with patch.dict(os.environ, {
            "SKPL_WEB_CONTENT_FORMATS": '["markdown", "text", "raw"]',
        }):
            cfg = WebSettings()
            assert cfg.content_formats == ["markdown", "text", "raw"]

    def test_ssrf_allowed_domains_from_string(self) -> None:
        """ssrf_allowed_domains parses JSON array string."""
        with patch.dict(os.environ, {
            "SKPL_WEB_SSRF_ALLOWED_DOMAINS": '["api.example.com", "cdn.example.com"]',
        }):
            cfg = WebSettings()
            assert cfg.ssrf_allowed_domains == ["api.example.com", "cdn.example.com"]


# ── UpdateSettings Tests ──────────────────────────────────────────────────


class TestUpdateSettings:
    """Tests for UpdateSettings (prefix: SKPL_UPDATE_)."""

    def test_default_values(self) -> None:
        """UpdateSettings has sensible defaults."""
        cfg = UpdateSettings()
        assert cfg.check_interval_hours == 6
        assert cfg.notify_on_update is True
        assert cfg.notify_channels == ["log"]
        assert cfg.webhook_url is None

    def test_upstream_repos_default(self) -> None:
        """upstream_repos includes the four default projects."""
        cfg = UpdateSettings()
        assert len(cfg.upstream_repos) == 4
        names = {r["name"] for r in cfg.upstream_repos}
        assert names == {"agentscope", "openwolf", "agent-s", "firecrawl"}
        for repo in cfg.upstream_repos:
            assert repo["enabled"] is True
            assert repo["branch"] == "main"

    def test_environment_variable_override(self) -> None:
        """SKPL_UPDATE_ vars override defaults."""
        with patch.dict(os.environ, {
            "SKPL_UPDATE_CHECK_INTERVAL_HOURS": "12",
            "SKPL_UPDATE_NOTIFY_ON_UPDATE": "false",
            "SKPL_UPDATE_WEBHOOK_URL": "https://hooks.example.com/notify",
        }):
            cfg = UpdateSettings()
            assert cfg.check_interval_hours == 12
            assert cfg.notify_on_update is False
            assert cfg.webhook_url == "https://hooks.example.com/notify"

    def test_notify_channels_from_string(self) -> None:
        """notify_channels parses JSON array string."""
        with patch.dict(os.environ, {
            "SKPL_UPDATE_NOTIFY_CHANNELS": '["log", "webhook", "email"]',
        }):
            cfg = UpdateSettings()
            assert cfg.notify_channels == ["log", "webhook", "email"]


# ── QuotaSettings Tests ───────────────────────────────────────────────────


class TestQuotaSettings:
    """Tests for QuotaSettings (prefix: SKPL_QUOTA_)."""

    def test_default_values(self) -> None:
        """QuotaSettings has sensible defaults."""
        cfg = QuotaSettings()
        assert cfg.default_max_agents == 10
        assert cfg.default_max_sessions == 50
        assert cfg.default_max_workspaces == 5
        assert cfg.default_max_desktop_nodes == 3
        assert cfg.default_max_web_requests_per_day == 10000
        assert cfg.default_max_token_budget == 1000000
        assert cfg.default_max_storage_mb == 1024

    def test_admin_overrides_default_empty(self) -> None:
        """admin_overrides defaults to empty dict."""
        cfg = QuotaSettings()
        assert cfg.admin_overrides == {}

    def test_environment_variable_override(self) -> None:
        """SKPL_QUOTA_ vars override defaults."""
        with patch.dict(os.environ, {
            "SKPL_QUOTA_DEFAULT_MAX_AGENTS": "5",
            "SKPL_QUOTA_DEFAULT_MAX_SESSIONS": "25",
            "SKPL_QUOTA_DEFAULT_MAX_TOKEN_BUDGET": "500000",
        }):
            cfg = QuotaSettings()
            assert cfg.default_max_agents == 5
            assert cfg.default_max_sessions == 25
            assert cfg.default_max_token_budget == 500000


# ── Unified Settings Tests ────────────────────────────────────────────────


class TestUnifiedSettings:
    """Tests for the unified Settings class."""

    def test_all_sub_configs_present(self) -> None:
        """Settings contains all sub-configuration objects."""
        cfg = Settings()
        assert isinstance(cfg.core, CoreSettings)
        assert isinstance(cfg.context, ContextSettings)
        assert isinstance(cfg.desktop, DesktopSettings)
        assert isinstance(cfg.web, WebSettings)
        assert isinstance(cfg.update, UpdateSettings)
        assert isinstance(cfg.quota, QuotaSettings)

    def test_sub_configs_use_defaults(self) -> None:
        """Sub-configs start with their respective defaults."""
        cfg = Settings()
        assert cfg.core.port == 8000
        assert cfg.context.token_budget == 200000
        assert cfg.desktop.ws_port == 8001
        assert cfg.web.crawler_timeout == 30
        assert cfg.update.check_interval_hours == 6
        assert cfg.quota.default_max_agents == 10

    def test_sub_config_env_override(self) -> None:
        """Sub-config fields are overridden via their env prefixes."""
        with patch.dict(os.environ, {
            "SKPL_CORE_PORT": "3000",
            "SKPL_CONTEXT_TOKEN_BUDGET": "999999",
            "SKPL_WEB_CRAWLER_TIMEOUT": "90",
        }):
            cfg = Settings()
            assert cfg.core.port == 3000
            assert cfg.context.token_budget == 999999
            assert cfg.web.crawler_timeout == 90


# ── Singleton Accessor Tests ──────────────────────────────────────────────


class TestGetSettings:
    """Tests for the get_settings() singleton function."""

    def test_returns_settings_instance(self) -> None:
        """get_settings() returns a Settings instance."""
        cfg = get_settings()
        assert isinstance(cfg, Settings)

    def test_cached_same_instance(self) -> None:
        """get_settings() returns the same cached instance."""
        cfg1 = get_settings()
        cfg2 = get_settings()
        assert cfg1 is cfg2

    def test_lru_cache_works(self) -> None:
        """The @lru_cache decorator ensures single instantiation."""
        import skpl_agent.config as config_mod
        # Clear the cache to verify it re-computes
        config_mod.get_settings.cache_clear()
        try:
            cfg1 = config_mod.get_settings()
            cfg2 = config_mod.get_settings()
            assert cfg1 is cfg2
        finally:
            config_mod.get_settings.cache_clear()