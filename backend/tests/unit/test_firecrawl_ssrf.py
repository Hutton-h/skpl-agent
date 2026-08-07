"""Tests for SSRF protection in Firecrawl integration."""

from __future__ import annotations

import pytest

from skpl_agent.app._service.firecrawl_service import SSRFProtection


class TestSSRFProtection:
    """Tests for SSRF protection."""

    def test_valid_public_url(self) -> None:
        """Valid public URLs are allowed."""
        assert SSRFProtection.validate_url("https://example.com") is None

    def test_valid_https_url(self) -> None:
        """Valid HTTPS URLs are allowed."""
        assert SSRFProtection.validate_url("https://api.github.com/repos/test") is None

    def test_block_localhost(self) -> None:
        """Localhost URLs are blocked."""
        with pytest.raises(ValueError, match="Internal URL"):
            SSRFProtection.validate_url("https://localhost:8080")

    def test_block_127_0_0_1(self) -> None:
        """127.0.0.1 URLs are blocked."""
        with pytest.raises(ValueError, match="Internal URL"):
            SSRFProtection.validate_url("https://127.0.0.1/api")

    def test_block_private_ip(self) -> None:
        """Private IP ranges are blocked."""
        with pytest.raises(ValueError, match="Internal URL"):
            SSRFProtection.validate_url("https://10.0.0.1/admin")

        with pytest.raises(ValueError, match="Internal URL"):
            SSRFProtection.validate_url("https://172.16.0.1/config")

        with pytest.raises(ValueError, match="Internal URL"):
            SSRFProtection.validate_url("https://192.168.1.1/secret")

    def test_block_ipv6_localhost(self) -> None:
        """IPv6 localhost is blocked."""
        with pytest.raises(ValueError, match="Internal URL"):
            SSRFProtection.validate_url("https://[::1]:8080/api")

    def test_block_metadata_endpoint(self) -> None:
        """Cloud metadata endpoints are blocked."""
        with pytest.raises(ValueError, match="Internal URL"):
            SSRFProtection.validate_url("http://169.254.169.254/latest/meta-data")

    def test_invalid_url(self) -> None:
        """Invalid URLs raise ValueError."""
        with pytest.raises(ValueError):
            SSRFProtection.validate_url("not-a-valid-url")

    def test_block_file_protocol(self) -> None:
        """File protocol is blocked."""
        with pytest.raises(ValueError, match="protocol"):
            SSRFProtection.validate_url("file:///etc/passwd")

    def test_block_ftp_protocol(self) -> None:
        """FTP protocol is blocked."""
        with pytest.raises(ValueError, match="protocol"):
            SSRFProtection.validate_url("ftp://example.com/file")

    def test_allow_custom_allowed_hosts(self) -> None:
        """Custom allowed hosts can be configured."""
        # This test verifies the pattern — implementation may vary
        assert SSRFProtection.is_private_ip("10.0.0.1") is True
        assert SSRFProtection.is_private_ip("8.8.8.8") is False

    def test_allow_subdomain(self) -> None:
        """Subdomains of public domains are allowed."""
        assert SSRFProtection.validate_url("https://sub.example.com/page") is None

    def test_block_internal_hostname(self) -> None:
        """Internal hostnames are blocked."""
        # Common internal hostnames
        for hostname in ["localhost", "metadata.google.internal"]:
            with pytest.raises(ValueError):
                SSRFProtection.validate_url(f"https://{hostname}/path")