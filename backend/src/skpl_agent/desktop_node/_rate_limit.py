"""Token bucket rate limiter for desktop action execution.

Extracted from app._service.rate_limit_service to avoid circular
dependencies and keep the rate limiting logic close to its usage.
"""

from __future__ import annotations

import time


class TokenBucket:
    """Token bucket rate limiter.

    Implements the token bucket algorithm for rate limiting.
    Tokens are consumed on each request and refilled at a constant rate.

    Usage:
        >>> bucket = TokenBucket(max_tokens=100, refill_rate=10)
        >>> bucket.consume()  # Returns True if tokens available
        >>> bucket.consume(5)  # Consume 5 tokens
    """

    def __init__(
        self,
        max_tokens: int,
        refill_rate: float,
        refill_period: float = 1.0,
    ) -> None:
        self._max_tokens = max_tokens
        self._refill_rate = refill_rate
        self._refill_period = refill_period
        self._tokens = float(max_tokens)
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        refill = elapsed * self._refill_rate
        self._tokens = min(self._max_tokens, self._tokens + refill)
        self._last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume.

        Returns:
            True if tokens were available and consumed.
        """
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    @property
    def available_tokens(self) -> int:
        """Get current available tokens."""
        self._refill()
        return int(self._tokens)

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    def time_until_refill(self, tokens_needed: int = 1) -> float:
        """Calculate seconds until enough tokens are available.

        Args:
            tokens_needed: Number of tokens needed.

        Returns:
            Seconds until enough tokens are available.
        """
        self._refill()
        if self._tokens >= tokens_needed:
            return 0.0
        deficit = tokens_needed - self._tokens
        return deficit / self._refill_rate