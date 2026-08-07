"""Tests for SensitiveContentFilter: detection and sanitization."""

import pytest
from skpl_agent.context.sensitive_filter import (
    SensitiveContentFilter,
    SensitiveMatch,
    SensitiveScanResult,
    SENSITIVE_FILENAME_PATTERNS,
    SENSITIVE_CONTENT_PATTERNS,
)


class TestFilenameBlacklist:
    """Filename-based sensitive content detection."""

    @pytest.fixture
    def filt(self):
        return SensitiveContentFilter()

    def test_env_files(self, filt):
        assert filt.is_sensitive_filename(".env") is True
        assert filt.is_sensitive_filename(".env.local") is True
        assert filt.is_sensitive_filename(".env.production") is True

    def test_key_files(self, filt):
        assert filt.is_sensitive_filename("id_rsa") is True
        assert filt.is_sensitive_filename("id_rsa.pub") is True
        assert filt.is_sensitive_filename("id_ed25519") is True
        assert filt.is_sensitive_filename("private.key") is True
        assert filt.is_sensitive_filename("server.pem") is True

    def test_secret_files(self, filt):
        assert filt.is_sensitive_filename("secrets.yml") is True
        assert filt.is_sensitive_filename("credentials.json") is True
        assert filt.is_sensitive_filename("service-account-key.json") is True

    def test_token_files(self, filt):
        assert filt.is_sensitive_filename("api_token.txt") is True
        assert filt.is_sensitive_filename("access_token") is True

    def test_normal_files(self, filt):
        assert filt.is_sensitive_filename("main.py") is False
        assert filt.is_sensitive_filename("README.md") is False
        assert filt.is_sensitive_filename("config.ts") is False
        assert filt.is_sensitive_filename("package.json") is False


class TestContentDetection:
    """Content-based sensitive information detection."""

    @pytest.fixture
    def filt(self):
        return SensitiveContentFilter()

    def test_api_key_assignment(self, filt):
        content = 'api_key = "sk-1234567890abcdefghijklmnopqrstuv"'
        assert filt.contains_sensitive_content(content) is True

    def test_aws_access_key(self, filt):
        content = "AKIAIOSFODNN7EXAMPLE"
        assert filt.contains_sensitive_content(content) is True

    def test_github_token(self, filt):
        content = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        assert filt.contains_sensitive_content(content) is True

    def test_jwt_token(self, filt):
        content = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        assert filt.contains_sensitive_content(content) is True

    def test_private_key(self, filt):
        content = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----"""
        assert filt.contains_sensitive_content(content) is True

    def test_connection_string(self, filt):
        content = "mongodb://admin:password123@localhost:27017/mydb"
        assert filt.contains_sensitive_content(content) is True

    def test_password_assignment(self, filt):
        content = 'password = "supersecret"'
        assert filt.contains_sensitive_content(content) is True

    def test_normal_content(self, filt):
        content = "def hello():\n    print('Hello, World!')"
        assert filt.contains_sensitive_content(content) is False

    def test_empty_content(self, filt):
        assert filt.contains_sensitive_content("") is False

    def test_scan_bytes_limit(self, filt):
        """Only first 512 bytes are scanned by default."""
        prefix = "x" * 600
        suffix = 'api_key = "sk-sensitive"'
        content = prefix + suffix
        # The sensitive part is beyond 512 bytes, should not be detected
        assert filt.contains_sensitive_content(content) is False


class TestSanitization:
    """Content sanitization (redaction)."""

    @pytest.fixture
    def filt(self):
        return SensitiveContentFilter()

    def test_sanitize_api_key(self, filt):
        content = 'api_key = "sk-1234567890abcdefghijklmnopqrstuv"'
        sanitized = filt.sanitize(content)
        assert "sk-1234567890abcdefghijklmnopqrstuv" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_password(self, filt):
        content = 'password = "mysecretpassword"'
        sanitized = filt.sanitize(content)
        assert "mysecretpassword" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_preserves_structure(self, filt):
        content = """config = {
    "api_key": "sk-1234567890abcdefghijklmnopqrstuv",
    "debug": True,
    "timeout": 30,
}"""
        sanitized = filt.sanitize(content)
        assert "debug" in sanitized
        assert "timeout" in sanitized
        assert "sk-1234567890abcdefghijklmnopqrstuv" not in sanitized

    def test_sanitize_no_sensitive(self, filt):
        content = "print('Hello World')"
        sanitized = filt.sanitize(content)
        assert sanitized == content


class TestFullScan:
    """Full scan returning SensitiveScanResult."""

    @pytest.fixture
    def filt(self):
        return SensitiveContentFilter()

    def test_scan_clean_content(self, filt):
        result = filt.scan("print('hello')", "main.py")
        assert result.is_sensitive is False
        assert result.filename_triggered is False
        assert len(result.matches) == 0

    def test_scan_sensitive_content(self, filt):
        content = 'api_key = "sk-1234567890abcdefghijklmnopqrstuv"'
        result = filt.scan(content, "config.py")
        assert result.is_sensitive is True
        assert len(result.matches) > 0

    def test_scan_sensitive_filename(self, filt):
        result = filt.scan("some content", ".env")
        assert result.is_sensitive is True
        assert result.filename_triggered is True

    def test_scan_returns_match_details(self, filt):
        content = 'api_key = "sk-1234567890abcdefghijklmnopqrstuv"'
        result = filt.scan(content, "test.py")
        assert len(result.matches) > 0
        match = result.matches[0]
        assert match.pattern is not None
        assert match.match_text is not None
        assert match.line_number > 0


class TestSensitiveMatchDataclass:
    """SensitiveMatch dataclass."""

    def test_create_match(self):
        match = SensitiveMatch(
            pattern="test_pattern",
            match_text="secret_value",
            line_number=5,
            severity="high",
        )
        assert match.pattern == "test_pattern"
        assert match.match_text == "secret_value"
        assert match.line_number == 5
        assert match.severity == "high"


class TestSensitiveScanResultDataclass:
    """SensitiveScanResult dataclass."""

    def test_default_values(self):
        result = SensitiveScanResult()
        assert result.is_sensitive is False
        assert result.matches == []
        assert result.filename_triggered is False

    def test_sensitive_result(self):
        result = SensitiveScanResult(
            is_sensitive=True,
            filename_triggered=True,
        )
        assert result.is_sensitive is True
        assert result.filename_triggered is True


class TestPatternCoverage:
    """Ensure expected patterns are defined."""

    def test_filename_patterns_present(self):
        assert len(SENSITIVE_FILENAME_PATTERNS) > 20
        assert ".env" in SENSITIVE_FILENAME_PATTERNS
        assert "id_rsa" in SENSITIVE_FILENAME_PATTERNS

    def test_content_patterns_present(self):
        assert len(SENSITIVE_CONTENT_PATTERNS) >= 10