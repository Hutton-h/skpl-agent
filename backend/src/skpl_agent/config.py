"""
SKPL Agent Unified Configuration

All configuration is managed through Pydantic Settings, with environment
variable overrides and .env file support. The config is loaded once at
startup and cached as a singleton.

Configuration categories:
- Core:     Server settings, database, secrets
- Context:  OpenWolf context management settings
- Desktop:  Agent-S desktop automation settings
- Web:      Firecrawl web scraping settings
- Update:   Upstream project update detection
- Quota:    Multi-tenant resource limits
"""

from __future__ import annotations

import logging
import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import (
    AnyHttpUrl,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Default placeholder that should never be used in production
_DEFAULT_SECRET_PLACEHOLDER = "your_secure_random_secret_here"


# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"


# ---------------------------------------------------------------------------
# Core Settings
# ---------------------------------------------------------------------------

class CoreSettings(BaseSettings):
    """Core server and infrastructure settings."""

    model_config = SettingsConfigDict(
        env_prefix="SKPL_CORE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = Field(default="0.0.0.0", description="Server bind address")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Uvicorn worker count")
    debug: bool = Field(default=False, description="Debug mode")

    # Database
    database_url: str = Field(
        default="",
        description="Async SQLAlchemy database URL (defaults to sqlite+aiosqlite:///{data_dir}/skpl.db)",
    )
    database_echo: bool = Field(default=False, description="SQL echo for debugging")

    # Redis
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")

    # Secrets
    secret_key: SecretStr = Field(
        default=SecretStr(_DEFAULT_SECRET_PLACEHOLDER),
        description="Secret key for JWT and session signing",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Log level",
    )
    log_format: Literal["json", "console"] = Field(
        default="json",
        description="Log format",
    )
    log_dir: Path = Field(default=DEFAULT_LOG_DIR, description="Log directory")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174",
                 "http://localhost:5175", "http://localhost:5176",
                 "http://localhost:5177", "http://localhost:5178",
                 "http://localhost:5179", "http://localhost:5180",
                 "http://localhost:4173"],
        description="Allowed CORS origins",
    )

    # Data directory
    data_dir: Path = Field(default=DEFAULT_DATA_DIR, description="Data storage directory")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @model_validator(mode="after")
    def _ensure_defaults(self) -> "CoreSettings":
        """Auto-generate defaults for missing configuration values."""
        # Auto-generate database URL if not set
        if not self.database_url:
            db_path = (self.data_dir / "skpl.db").as_posix()
            self.database_url = f"sqlite+aiosqlite:///{db_path}"
        # Auto-generate a random secret key if the default placeholder is used
        if self.secret_key.get_secret_value() == _DEFAULT_SECRET_PLACEHOLDER:
            self.secret_key = SecretStr(secrets.token_urlsafe(48))
            logger.warning(
                "WARNING: SKPL_CORE_SECRET_KEY not set — using auto-generated key. "
                "Set SKPL_CORE_SECRET_KEY in your .env file for production deployments."
            )
        return self


# ---------------------------------------------------------------------------
# Context Settings (OpenWolf)
# ---------------------------------------------------------------------------

class ContextSettings(BaseSettings):
    """OpenWolf context management settings."""

    model_config = SettingsConfigDict(
        env_prefix="SKPL_CONTEXT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Anatomy Store
    anatomy_store_path: Path = Field(
        default=DEFAULT_DATA_DIR / "anatomy_store.db",
        description="Path to the anatomy SQLite database",
    )
    anatomy_use_json: bool = Field(
        default=False,
        description="Use JSON file mode instead of SQLite",
    )
    anatomy_json_path: Path = Field(
        default=DEFAULT_DATA_DIR / "anatomy_store.json",
        description="Path to the anatomy JSON file",
    )

    # Scanning
    scan_include_patterns: list[str] = Field(
        default=["**/*.py", "**/*.ts", "**/*.tsx", "**/*.js", "**/*.go",
                 "**/*.rs", "**/*.java", "**/*.c", "**/*.cpp", "**/*.h", "**/*.hpp"],
        description="Glob patterns for files to scan",
    )
    scan_exclude_patterns: list[str] = Field(
        default=["**/node_modules/**", "**/__pycache__/**", "**/.git/**",
                 "**/dist/**", "**/build/**", "**/.venv/**", "**/venv/**",
                 "**/*.min.js", "**/*.min.css", "**/vendor/**"],
        description="Glob patterns for files to exclude",
    )
    scan_max_file_size_mb: int = Field(default=5, description="Max file size to scan in MB")
    scan_interval_seconds: int = Field(default=300, description="Polling interval for file changes")
    scan_parallel_workers: int = Field(default=4, description="Parallel scan workers")

    # Token Management
    token_budget: int = Field(default=200000, description="Default token budget")
    token_waste_threshold: float = Field(
        default=0.30,
        description="Fraction of token budget that triggers waste detection",
    )
    token_ledger_flush_interval: int = Field(
        default=60,
        description="Seconds between token ledger flushes",
    )

    # BugLog
    buglog_jaccard_threshold: float = Field(
        default=0.75,
        description="Jaccard similarity threshold for bug deduplication",
    )
    buglog_max_entries: int = Field(default=10000, description="Max buglog entries")

    # Sensitive Content
    sensitive_patterns: list[str] = Field(
        default=[
            r"(?i)(api[_-]?key|api[_-]?secret|access[_-]?key|secret[_-]?key)",
            r"(?i)(password|passwd|pwd|secret|token)",
            r"(?i)(private[_-]?key|ssh[_-]?key|rsa[_-]?key)",
            r"\b[A-Za-z0-9+/]{40,}={0,2}\b",  # Base64-like strings
        ],
        description="Regex patterns for sensitive content detection",
    )
    sensitive_file_patterns: list[str] = Field(
        default=["**/.env", "**/.env.*", "**/credentials.*", "**/*.pem",
                 "**/*.key", "**/secrets.*", "**/config.*.local"],
        description="Glob patterns for sensitive files",
    )

    @field_validator("scan_include_patterns", "scan_exclude_patterns", "sensitive_patterns", "sensitive_file_patterns", mode="before")
    @classmethod
    def parse_list(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


# ---------------------------------------------------------------------------
# Desktop Settings (Agent-S)
# ---------------------------------------------------------------------------

class DesktopSettings(BaseSettings):
    """Agent-S desktop automation settings."""

    model_config = SettingsConfigDict(
        env_prefix="SKPL_DESKTOP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # WebSocket
    ws_host: str = Field(default="0.0.0.0", description="WebSocket bind address")
    ws_port: int = Field(default=8001, description="WebSocket port")
    ws_heartbeat_interval: int = Field(default=10, description="Heartbeat interval in seconds")
    ws_reconnect_backoff_base: float = Field(default=1.0, description="Base for exponential backoff")
    ws_reconnect_backoff_max: float = Field(default=60.0, description="Max backoff in seconds")
    ws_token_expiry: int = Field(default=3600, description="JWT token expiry in seconds")

    # Node Management
    node_max_offline_seconds: int = Field(default=60, description="Max offline time before marking dead")
    node_cleanup_interval: int = Field(default=30, description="Node cleanup interval in seconds")

    # Rate Limiting (Token Bucket)
    desktop_rate_limit_per_minute: int = Field(
        default=60,
        description="Max desktop actions per node per minute",
    )
    desktop_rate_limit_burst: int = Field(
        default=10,
        description="Max burst actions per node",
    )

    # Action Timeout
    action_timeout_seconds: int = Field(default=30, description="Default action timeout")
    screenshot_timeout_seconds: int = Field(default=10, description="Screenshot timeout")
    ocr_timeout_seconds: int = Field(default=30, description="OCR timeout")

    # Grounding
    grounding_model: str = Field(
        default="microsoft/OmniParser-v2",
        description="Grounding model name",
    )
    grounding_device: Literal["cpu", "cuda", "mps"] = Field(
        default="cpu",
        description="Grounding model device",
    )

    # OCR
    ocr_enabled: bool = Field(default=True, description="Enable OCR")
    ocr_lang: str = Field(default="ch", description="OCR language")


# ---------------------------------------------------------------------------
# Web Settings (Firecrawl)
# ---------------------------------------------------------------------------

class WebSettings(BaseSettings):
    """Firecrawl web scraping settings."""

    model_config = SettingsConfigDict(
        env_prefix="SKPL_WEB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Crawler
    crawler_user_agent: str = Field(
        default="SKPL-Agent/1.0 (Research Crawler; +https://skpl-agent.dev/bot)",
        description="User-Agent for web requests",
    )
    crawler_timeout: int = Field(default=30, description="Request timeout in seconds")
    crawler_max_redirects: int = Field(default=5, description="Max redirects")
    crawler_concurrency: int = Field(default=3, description="Max concurrent crawls")
    crawler_delay: float = Field(default=1.0, description="Delay between requests to same domain")

    # SSRF Protection
    ssrf_enabled: bool = Field(default=True, description="Enable SSRF protection")
    ssrf_allowed_domains: list[str] = Field(
        default=[],
        description="Explicitly allowed domains (whitelist)",
    )
    ssrf_blocked_networks: list[str] = Field(
        default=["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
                 "127.0.0.0/8", "169.254.0.0/16", "0.0.0.0/8"],
        description="Blocked private network ranges",
    )
    ssrf_block_localhost: bool = Field(default=True, description="Block localhost")
    ssrf_dns_rebinding_protection: bool = Field(
        default=True,
        description="Enable DNS rebinding protection",
    )

    # Content
    content_max_size_mb: int = Field(default=50, description="Max content size to download")
    content_formats: list[str] = Field(
        default=["markdown", "html", "text"],
        description="Output formats to generate",
    )

    # Rate Limiting
    web_rate_limit_per_minute: int = Field(
        default=30,
        description="Max web requests per tenant per minute",
    )

    @field_validator("ssrf_allowed_domains", "content_formats", mode="before")
    @classmethod
    def parse_list(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


# ---------------------------------------------------------------------------
# Update Settings
# ---------------------------------------------------------------------------

class UpdateSettings(BaseSettings):
    """Upstream project update detection settings."""

    model_config = SettingsConfigDict(
        env_prefix="SKPL_UPDATE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Check interval
    check_interval_hours: int = Field(default=6, description="Hours between update checks")

    # Upstream repos
    upstream_repos: list[dict] = Field(
        default=[
            {
                "name": "agentscope",
                "url": "https://github.com/agentscope-ai/agentscope",
                "branch": "main",
                "enabled": True,
            },
            {
                "name": "openwolf",
                "url": "https://github.com/nicklausroach/OpenWolf",
                "branch": "main",
                "enabled": True,
            },
            {
                "name": "agent-s",
                "url": "https://github.com/simular-ai/Agent-S",
                "branch": "main",
                "enabled": True,
            },
            {
                "name": "firecrawl",
                "url": "https://github.com/mendableai/firecrawl",
                "branch": "main",
                "enabled": True,
            },
        ],
        description="Upstream repositories to track",
    )

    # Notification
    notify_on_update: bool = Field(default=True, description="Send notifications on updates")
    notify_channels: list[str] = Field(
        default=["log"],
        description="Notification channels: log, webhook, email",
    )
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for notifications")

    @field_validator("notify_channels", mode="before")
    @classmethod
    def parse_channels(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [c.strip() for c in v.split(",") if c.strip()]
        return v


# ---------------------------------------------------------------------------
# Auth Settings
# ---------------------------------------------------------------------------

class AuthSettings(BaseSettings):
    """Authentication settings — dual-mode transition support.

    When ``mode=none``, the existing X-User-ID header authentication
    is used (backward compatible).  When ``mode=jwt``, JWT Bearer
    tokens are required; X-User-ID is still accepted as a fallback
    during the transition period.
    """

    model_config = SettingsConfigDict(
        env_prefix="SKPL_AUTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mode: Literal["none", "jwt"] = Field(
        default="none",
        description="Auth mode: 'none' = X-User-ID header only, 'jwt' = JWT Bearer token (with X-User-ID fallback)",
    )
    jwt_secret: str = Field(
        default=_DEFAULT_SECRET_PLACEHOLDER,
        description="JWT secret key for token signing",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
    )
    jwt_expiry_hours: int = Field(
        default=24,
        description="JWT token expiry in hours",
    )

    @model_validator(mode="after")
    def _ensure_jwt_secret(self) -> "AuthSettings":
        """Auto-generate a random JWT secret if the default placeholder is used."""
        if self.jwt_secret == _DEFAULT_SECRET_PLACEHOLDER:
            self.jwt_secret = secrets.token_urlsafe(48)
            logger.warning(
                "WARNING: SKPL_AUTH_JWT_SECRET not set — using auto-generated key. "
                "Set SKPL_AUTH_JWT_SECRET in your .env file for production deployments."
            )
        return self


# ---------------------------------------------------------------------------
# Quota Settings
# ---------------------------------------------------------------------------

class QuotaSettings(BaseSettings):
    """Multi-tenant resource quota settings."""

    model_config = SettingsConfigDict(
        env_prefix="SKPL_QUOTA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Default tenant quotas
    default_max_agents: int = Field(default=10, description="Max agents per tenant")
    default_max_sessions: int = Field(default=50, description="Max sessions per tenant")
    default_max_workspaces: int = Field(default=5, description="Max workspaces per tenant")
    default_max_desktop_nodes: int = Field(default=3, description="Max desktop nodes per tenant")
    default_max_web_requests_per_day: int = Field(
        default=10000,
        description="Max web requests per tenant per day",
    )
    default_max_token_budget: int = Field(
        default=1000000,
        description="Max token budget per tenant",
    )
    default_max_storage_mb: int = Field(default=1024, description="Max storage per tenant in MB")

    # Admin overrides
    admin_overrides: dict[str, dict] = Field(
        default={},
        description="Per-tenant quota overrides for admin",
    )


# ---------------------------------------------------------------------------
# Mem0 Settings (L2 Semantic Memory)
# ---------------------------------------------------------------------------

class Mem0Settings(BaseSettings):
    """Mem0 local OSS deployment settings for L2 semantic memory.

    Uses Chroma as the in-process vector store (no external service
    required). LLM and embedding providers default to Ollama for a
    fully local setup, with OpenAI as an alternative.
    """

    model_config = SettingsConfigDict(
        env_prefix="SKPL_MEM0_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Enable/disable Mem0
    enabled: bool = Field(default=True, description="Enable Mem0 L2 memory")

    # Vector store — Chroma runs in-process, no external service
    vector_store_provider: Literal["chroma", "qdrant"] = Field(
        default="chroma",
        description="Vector store provider",
    )
    chroma_path: str = Field(
        default="",
        description="Chroma persistence path (default: data/mem0_chroma)",
    )
    chroma_collection: str = Field(
        default="skpl_mem0",
        description="Chroma collection name",
    )

    # LLM provider for memory extraction
    llm_provider: Literal["ollama", "openai", "deepseek", "lmstudio"] = Field(
        default="ollama",
        description="LLM provider for Mem0 memory extraction",
    )
    llm_model: str = Field(
        default="qwen2.5:7b",
        description="LLM model name",
    )
    llm_base_url: str = Field(
        default="",
        description="LLM API base URL (for OpenAI-compatible providers)",
    )
    llm_api_key: str = Field(
        default="",
        description="LLM API key",
    )

    # Embedding provider
    embedder_provider: Literal["ollama", "openai", "huggingface", "fastembed"] = Field(
        default="fastembed",
        description="Embedding provider for Mem0 (fastembed: local, no API key needed)",
    )
    embedder_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="Embedding model name (fastembed default: BAAI/bge-small-en-v1.5)",
    )
    embedder_base_url: str = Field(
        default="",
        description="Embedding API base URL",
    )
    embedder_api_key: str = Field(
        default="",
        description="Embedding API key",
    )

    # History DB
    history_db_path: str = Field(
        default="",
        description="Mem0 history DB path (default: data/mem0_history.db)",
    )


# ---------------------------------------------------------------------------
# Unified Settings
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    """Unified SKPL Agent settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    core: CoreSettings = Field(default_factory=CoreSettings)
    context: ContextSettings = Field(default_factory=ContextSettings)
    desktop: DesktopSettings = Field(default_factory=DesktopSettings)
    web: WebSettings = Field(default_factory=WebSettings)
    update: UpdateSettings = Field(default_factory=UpdateSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    quota: QuotaSettings = Field(default_factory=QuotaSettings)
    mem0: Mem0Settings = Field(default_factory=Mem0Settings)


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings singleton.

    The settings are loaded on first call and cached for the lifetime
    of the process. Use this function instead of instantiating Settings
    directly.
    """
    return Settings()


# Convenience alias
settings = get_settings()