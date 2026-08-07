"""SSRF Protection — prevents Server-Side Request Forgery attacks.

Validates and sanitizes URLs before making outbound requests to prevent:
- Internal network probing (10.x, 172.16.x, 192.168.x)
- Localhost access (127.0.0.1, ::1, localhost)
- DNS rebinding attacks
- Cloud metadata service access (169.254.169.254)
- File:// and other dangerous protocols
"""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Blocked network ranges
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved
]

# Blocked hostnames
_BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "169.254.169.254",
}

# Allowed protocols
_ALLOWED_PROTOCOLS = {"http", "https"}


class SSRFError(Exception):
    """Raised when a URL is blocked by SSRF protection."""


class SSRFProtection:
    """URL validation and sanitization for SSRF prevention.

    Usage:
        >>> protector = SSRFProtection()
        >>> protector.validate_url("https://example.com")  # OK
        >>> protector.validate_url("http://localhost:8080")  # Raises SSRFError
        >>> protector.validate_url("http://169.254.169.254/")  # Raises SSRFError
    """

    def __init__(
        self,
        allowed_domains: list[str] | None = None,
        blocked_networks: list[str] | None = None,
        block_localhost: bool = True,
        dns_rebinding_protection: bool = True,
    ) -> None:
        self._allowed_domains: set[str] = set(allowed_domains or [])
        self._block_localhost = block_localhost
        self._dns_rebinding_protection = dns_rebinding_protection

        # Build blocked networks
        self._blocked_networks = list(_BLOCKED_NETWORKS)
        if blocked_networks:
            for net in blocked_networks:
                try:
                    self._blocked_networks.append(ipaddress.ip_network(net))
                except ValueError:
                    logger.warning("Invalid blocked network: %s", net)

    # ── URL Validation ───────────────────────────────────────────────────

    def validate_url(self, url: str) -> None:
        """Validate a URL for SSRF safety.

        Args:
            url: The URL to validate.

        Raises:
            SSRFError: If the URL is blocked.
        """
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception:
            raise SSRFError(f"Invalid URL format: {url}")

        # Check protocol
        if parsed.scheme.lower() not in _ALLOWED_PROTOCOLS:
            raise SSRFError(
                f"Protocol '{parsed.scheme}' is not allowed. "
                f"Only {_ALLOWED_PROTOCOLS} are permitted."
            )

        hostname = parsed.hostname
        if not hostname:
            raise SSRFError(f"No hostname in URL: {url}")

        # Check allowed domains (whitelist)
        if self._allowed_domains:
            if not any(
                hostname == domain or hostname.endswith(f".{domain}")
                for domain in self._allowed_domains
            ):
                raise SSRFError(
                    f"Domain '{hostname}' is not in the allowed domains list."
                )

        # Check blocked hostnames
        if hostname.lower() in _BLOCKED_HOSTNAMES:
            raise SSRFError(f"Hostname '{hostname}' is blocked.")

        # Check if hostname is a known blocked pattern
        if self._block_localhost and self._is_localhost(hostname):
            raise SSRFError(f"Localhost access is blocked: {hostname}")

        # Resolve and check IP
        try:
            ip = socket.gethostbyname(hostname)
        except socket.gaierror:
            raise SSRFError(f"Could not resolve hostname: {hostname}")

        self.validate_ip(ip)

        # DNS rebinding check
        if self._dns_rebinding_protection:
            self._check_dns_rebinding(hostname, ip)

    def validate_ip(self, ip_str: str) -> None:
        """Validate an IP address for SSRF safety.

        Args:
            ip_str: IP address string.

        Raises:
            SSRFError: If the IP is in a blocked range.
        """
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise SSRFError(f"Invalid IP address: {ip_str}")

        for network in self._blocked_networks:
            if ip in network:
                raise SSRFError(
                    f"IP address {ip} is in blocked range {network}."
                )

    def sanitize_url(self, url: str) -> str:
        """Sanitize a URL by removing fragments and userinfo.

        Args:
            url: URL to sanitize.

        Returns:
            Sanitized URL string.
        """
        parsed = urlparse(url)

        # Remove userinfo (username:password@)
        # Remove fragment (#section)
        sanitized = parsed._replace(
            netloc=parsed.hostname + (
                f":{parsed.port}" if parsed.port else ""
            ),
            fragment="",
        )

        return sanitized.geturl()

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _is_localhost(hostname: str) -> bool:
        """Check if a hostname refers to localhost."""
        hostname_lower = hostname.lower()
        return (
            hostname_lower == "localhost"
            or hostname_lower == "localhost.localdomain"
            or hostname_lower.endswith(".local")
            or hostname_lower == "0.0.0.0"
        )

    def _check_dns_rebinding(self, hostname: str, ip: str) -> None:
        """Check for DNS rebinding by resolving again.

        DNS rebinding attacks change the IP between the first and second
        resolution. We resolve twice and compare.
        """
        try:
            ip2 = socket.gethostbyname(hostname)
            if ip != ip2:
                logger.warning(
                    "DNS rebinding detected: %s -> %s (first) vs %s (second)",
                    hostname, ip, ip2,
                )
                raise SSRFError(
                    f"DNS rebinding detected for {hostname}: "
                    f"IP changed from {ip} to {ip2}"
                )
        except socket.gaierror:
            pass  # If second resolution fails, use first result

    def is_url_allowed(self, url: str) -> bool:
        """Check if a URL is allowed without raising.

        Returns:
            True if the URL is safe, False otherwise.
        """
        try:
            self.validate_url(url)
            return True
        except SSRFError:
            return False

    def filter_urls(self, urls: list[str]) -> list[str]:
        """Filter a list of URLs, returning only safe ones.

        Args:
            urls: List of URLs to filter.

        Returns:
            List of safe URLs.
        """
        safe_urls: list[str] = []
        for url in urls:
            if self.is_url_allowed(url):
                safe_urls.append(url)
            else:
                logger.debug("URL blocked by SSRF: %s", url)
        return safe_urls