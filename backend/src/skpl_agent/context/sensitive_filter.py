"""
Sensitive Content Filter — Detects and sanitizes sensitive files.

Three-layer protection:
1. Filename blacklist: block known sensitive file patterns
2. Content detection: scan first 512 bytes for secrets/keys/tokens
3. Sanitization: redact sensitive content before injecting into context

Based on the security architecture from the final plan (Section 7.2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Filename Blacklist
# ---------------------------------------------------------------------------

SENSITIVE_FILENAME_PATTERNS: list[str] = [
    # Environment files
    ".env",
    ".env.*",
    "*.env",
    "env.local",
    "env.production",
    # Key/certificate files
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.crt",
    "*.cer",
    "*.der",
    "*.jks",
    "*.keystore",
    "*.truststore",
    "id_rsa",
    "id_rsa.*",
    "id_ed25519",
    "id_ecdsa",
    "*.ppk",
    # Secret/credential files
    "*secret*",
    "*credential*",
    "*credentials*",
    "*password*",
    "*token*",
    "*api_key*",
    "*apikey*",
    "*private_key*",
    "*privatekey*",
    "*access_key*",
    # Configuration files with secrets
    "*.secrets",
    "*.secret",
    "secrets.yml",
    "secrets.yaml",
    "secrets.json",
    "credentials.json",
    "service-account*.json",
    "google-credentials.json",
    # Cloud/CI config
    ".terraform/*",
    ".tfstate",
    "terraform.tfvars",
    "kubeconfig",
    ".kube/config",
    # Other
    ".npmrc",
    ".pypirc",
    ".netrc",
    ".htpasswd",
    "master.key",
    "production.key",
    "database.yml",
]


# ---------------------------------------------------------------------------
# Content Detection Patterns
# ---------------------------------------------------------------------------

SENSITIVE_CONTENT_PATTERNS: list[re.Pattern] = [
    # Private keys
    re.compile(r"-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PGP)\s+PRIVATE\s+KEY", re.IGNORECASE),
    re.compile(r"-----BEGIN\s+PRIVATE\s+KEY", re.IGNORECASE),
    # API keys and tokens
    re.compile(r'(?:api[_-]?key|apikey|api[_-]?secret|api[_-]?token)["\']?\s*[:=]\s*["\']?[\w\-_]{20,}["\']?', re.IGNORECASE),
    re.compile(r'(?:access[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*["\']?[\w\-_+/=]{20,}["\']?', re.IGNORECASE),
    re.compile(r'(?:password|passwd|pwd)\s*[:=]\s*["\']?[^\s"\']{4,}["\']?', re.IGNORECASE),
    # AWS keys
    re.compile(r'AKIA[0-9A-Z]{16}'),
    re.compile(r'(?:aws[_-]?secret|aws[_-]?access)\s*[:=]\s*["\']?[\w/+]{20,}["\']?', re.IGNORECASE),
    # GitHub tokens
    re.compile(r'(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}'),
    re.compile(r'github[_-]?token\s*[:=]\s*["\']?[\w_]{20,}["\']?', re.IGNORECASE),
    # Stripe keys
    re.compile(r'(?:sk_live|pk_live|rk_live)_[A-Za-z0-9]{24,}'),
    # JWT tokens
    re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'),
    # Generic secret patterns
    re.compile(r'(?:secret|token|key|auth)\s*[:=]\s*["\']?[\w\-_+/=]{32,}["\']?', re.IGNORECASE),
    # Connection strings
    re.compile(r'(?:mongodb|postgres|mysql|redis|jdbc)://[^\s"\']+@', re.IGNORECASE),
    # Private IPs and internal URLs (in env files)
    re.compile(r'(?:host|server|endpoint|url)\s*[:=]\s*["\']?(?:https?://)?(?:10\.|172\.(?:1[6-9]|2\d|3[01])\.|192\.168\.|127\.0\.0\.1|localhost|0\.0\.0\.0)', re.IGNORECASE),
]


@dataclass
class SensitiveMatch:
    """Result of a sensitive content scan."""

    pattern: str
    match_text: str
    line_number: int
    severity: str = "high"  # high, medium, low


@dataclass
class SensitiveScanResult:
    """Full result of a sensitive content scan."""

    is_sensitive: bool = False
    matches: list[SensitiveMatch] = field(default_factory=list)
    filename_triggered: bool = False


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------


class SensitiveContentFilter:
    """Detects and sanitizes sensitive content in files.

    Usage:
        filt = SensitiveContentFilter()
        if filt.is_sensitive_filename("id_rsa"):
            print("Sensitive file, skip scanning")
        if filt.contains_sensitive_content(source_code):
            print("Sensitive content found, needs sanitization")
        safe = filt.sanitize(source_code)
    """

    def __init__(
        self,
        filename_patterns: list[str] | None = None,
        content_patterns: list[re.Pattern] | None = None,
        scan_bytes: int = 512,
    ):
        self.filename_patterns = filename_patterns or SENSITIVE_FILENAME_PATTERNS
        self.content_patterns = content_patterns or SENSITIVE_CONTENT_PATTERNS
        self.scan_bytes = scan_bytes

    def is_sensitive_filename(self, filename: str) -> bool:
        """Check if the filename matches any sensitive pattern."""
        for pattern in self.filename_patterns:
            if Path(filename).match(pattern):
                return True
        return False

    def contains_sensitive_content(self, content: str) -> bool:
        """Check if content contains sensitive information.

        Only scans the first `scan_bytes` bytes for performance.
        """
        scan_content = content[: self.scan_bytes]
        for pattern in self.content_patterns:
            if pattern.search(scan_content):
                return True
        return False

    def scan(self, content: str, filename: str = "") -> SensitiveScanResult:
        """Full scan of content, returning all matches."""
        result = SensitiveScanResult()

        if filename and self.is_sensitive_filename(filename):
            result.filename_triggered = True
            result.is_sensitive = True

        lines = content.split("\n")
        for pattern in self.content_patterns:
            for i, line in enumerate(lines[:20]):  # Only scan first 20 lines
                match = pattern.search(line)
                if match:
                    result.is_sensitive = True
                    result.matches.append(
                        SensitiveMatch(
                            pattern=pattern.pattern,
                            match_text=match.group(0),
                            line_number=i + 1,
                        )
                    )

        return result

    def sanitize(self, content: str) -> str:
        """Sanitize content by redacting sensitive patterns.

        Replaces sensitive values with [REDACTED] placeholders while
        preserving the structure of the content.
        """
        sanitized = content

        for pattern in self.content_patterns:
            sanitized = pattern.sub("[REDACTED]", sanitized)

        return sanitized

    def sanitize_file(self, file_path: str | Path) -> Optional[str]:
        """Read, sanitize, and return file content.

        Returns None if the file is on the filename blacklist.
        """
        path = Path(file_path)

        if self.is_sensitive_filename(path.name):
            return None

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        if self.contains_sensitive_content(content):
            return self.sanitize(content)

        return content

    def get_file_summary(self, file_path: str | Path) -> Optional[str]:
        """Get a safe summary of a file, even if sensitive.

        Returns the first 5 non-sensitive lines, or None if the file
        is completely blacklisted.
        """
        path = Path(file_path)

        if self.is_sensitive_filename(path.name):
            return None

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        lines = content.split("\n")
        safe_lines: list[str] = []

        for line in lines[:50]:
            is_sensitive = False
            for pattern in self.content_patterns:
                if pattern.search(line):
                    is_sensitive = True
                    break
            if not is_sensitive:
                safe_lines.append(line)
            if len(safe_lines) >= 5:
                break

        return "\n".join(safe_lines) if safe_lines else None