"""Token-bucket rate limiter for AI API calls.

Provides per-provider rate limiting using the token bucket algorithm
with configurable RPM limits, burst allowance, and thread-safe operation.
"""

import logging
import threading
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)

_BURST_MULTIPLIER: float = 1.5


class AIRateLimiter:
    """Token-bucket rate limiter with per-provider configuration.

    Each provider gets an independent bucket that refills at a steady rate.
    A burst allowance of 1.5× the normal capacity is supported so that
    short spikes in traffic are absorbed without immediate rejection.

    Args:
        default_rpm: Default requests-per-minute applied to any provider
            that has not been explicitly configured via :meth:`configure`.
    """

    def __init__(self, default_rpm: int = 60) -> None:
        if default_rpm <= 0:
            raise ValueError("default_rpm must be a positive integer")

        self._default_rpm: int = default_rpm
        self._lock: threading.Lock = threading.Lock()
        self._buckets: Dict[str, "_TokenBucket"] = {}

        logger.info("AIRateLimiter initialised with default_rpm=%d", default_rpm)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def configure(self, provider: str, rpm: int) -> None:
        """Set (or update) the rate limit for *provider*.

        If the provider already has a bucket it is replaced, resetting
        its token count to the new maximum.

        Args:
            provider: Identifier for the AI provider (e.g. ``"openai"``).
            rpm: Requests-per-minute allowed for this provider.

        Raises:
            ValueError: If *rpm* is not a positive integer.
        """
        if rpm <= 0:
            raise ValueError(f"rpm must be a positive integer, got {rpm}")

        with self._lock:
            self._buckets[provider] = _TokenBucket(rpm)
            logger.info(
                "Configured provider '%s' with rpm=%d (burst=%d)",
                provider,
                rpm,
                int(rpm * _BURST_MULTIPLIER),
            )

    def acquire(self, provider: str) -> bool:
        """Try to consume one token from *provider*'s bucket.

        If the provider has not been configured, a bucket is created
        automatically using :pyattr:`_default_rpm`.

        Returns:
            ``True`` if a token was available and consumed, ``False``
            otherwise.
        """
        with self._lock:
            bucket = self._ensure_bucket(provider)
            allowed = bucket.consume()

        if allowed:
            logger.debug("Token acquired for provider '%s'", provider)
        else:
            logger.warning(
                "Rate limit reached for provider '%s' — request rejected",
                provider,
            )
        return allowed

    def wait_time(self, provider: str) -> float:
        """Return the number of seconds until the next token is available.

        A return value of ``0.0`` means a token can be acquired
        immediately.
        """
        with self._lock:
            bucket = self._ensure_bucket(provider)
            return bucket.time_until_available()

    def get_usage(self, provider: str) -> Dict[str, Any]:
        """Return a snapshot of usage statistics for *provider*.

        Keys in the returned dict:

        * **provider** – provider name.
        * **rpm_limit** – configured requests-per-minute.
        * **burst_limit** – maximum burst capacity (1.5× rpm).
        * **tokens_remaining** – tokens currently in the bucket.
        * **requests_consumed** – total requests consumed since creation
          or last :meth:`configure`.
        * **wait_seconds** – seconds until the next token is available.
        * **refill_rate_per_sec** – tokens added per second.
        """
        with self._lock:
            bucket = self._ensure_bucket(provider)
            bucket.refill()
            return {
                "provider": provider,
                "rpm_limit": bucket.rpm,
                "burst_limit": bucket.max_tokens,
                "tokens_remaining": round(bucket.tokens, 2),
                "requests_consumed": bucket.total_consumed,
                "wait_seconds": round(bucket.time_until_available(), 4),
                "refill_rate_per_sec": round(bucket.refill_rate, 4),
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_bucket(self, provider: str) -> "_TokenBucket":
        """Return the bucket for *provider*, creating one if necessary.

        Must be called while holding :pyattr:`_lock`.
        """
        if provider not in self._buckets:
            self._buckets[provider] = _TokenBucket(self._default_rpm)
            logger.debug(
                "Auto-created bucket for provider '%s' with default rpm=%d",
                provider,
                self._default_rpm,
            )
        return self._buckets[provider]


class _TokenBucket:
    """Internal token-bucket implementation.

    Tokens refill continuously at ``rpm / 60`` tokens-per-second.  The
    bucket capacity is ``rpm * BURST_MULTIPLIER`` so that short bursts
    exceeding the steady-state rate are tolerated.

    This class is **not** thread-safe on its own; synchronisation is
    handled by :class:`AIRateLimiter`.
    """

    __slots__ = (
        "rpm",
        "max_tokens",
        "refill_rate",
        "tokens",
        "total_consumed",
        "_last_refill",
    )

    def __init__(self, rpm: int) -> None:
        self.rpm: int = rpm
        self.max_tokens: int = int(rpm * _BURST_MULTIPLIER)
        self.refill_rate: float = rpm / 60.0
        self.tokens: float = float(self.max_tokens)
        self.total_consumed: int = 0
        self._last_refill: float = time.monotonic()

    # ------------------------------------------------------------------

    def refill(self) -> None:
        """Add tokens that have accumulated since the last refill."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        if elapsed <= 0.0:
            return
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self._last_refill = now

    def consume(self) -> bool:
        """Try to take one token. Returns ``True`` on success."""
        self.refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            self.total_consumed += 1
            return True
        return False

    def time_until_available(self) -> float:
        """Seconds until at least one full token is available."""
        self.refill()
        if self.tokens >= 1.0:
            return 0.0
        deficit = 1.0 - self.tokens
        return deficit / self.refill_rate
