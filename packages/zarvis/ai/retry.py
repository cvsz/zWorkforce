"""Advanced retry strategy with exponential backoff and jitter.

Provides :class:`AIRetryStrategy` for executing callables with automatic
retry logic, and the :func:`with_retry` decorator for declarative usage.

Example::

    strategy = AIRetryStrategy(max_retries=5, base_delay=0.5)
    result = strategy.execute(call_remote_api, prompt="hello")

    @with_retry(max_retries=3)
    def fetch_embedding(text: str) -> list[float]:
        ...
"""

from __future__ import annotations

import functools
import logging
import random
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_RETRYABLE_KEYWORDS: tuple[str, ...] = (
    "rate_limit",
    "429",
    "503",
    "502",
)

_NON_RETRYABLE_TYPES: tuple[type[Exception], ...] = (
    ValueError,
    KeyError,
)


class AIRetryStrategy:
    """Execute a callable with exponential-backoff retry logic.

    Parameters
    ----------
    max_retries:
        Maximum number of retry attempts (excludes the initial call).
    base_delay:
        Base delay in seconds before the first retry.
    max_delay:
        Upper bound for the computed delay (caps exponential growth).
    exponential_base:
        Multiplier applied on each successive attempt.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if base_delay <= 0:
            raise ValueError("base_delay must be > 0")
        if max_delay < base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if exponential_base < 1:
            raise ValueError("exponential_base must be >= 1")

        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute *fn* with retry logic.

        The function is called once, then retried up to *max_retries* times
        if a retryable exception is raised.  Between attempts the thread
        sleeps for the delay returned by :meth:`calculate_delay`.

        Returns
        -------
        Any
            The return value of *fn*.

        Raises
        ------
        Exception
            The last exception if all attempts are exhausted, or any
            non-retryable exception immediately.
        """
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                last_exception = exc

                if not self.should_retry(exc):
                    logger.error(
                        "Non-retryable error on attempt %d/%d: %s",
                        attempt + 1,
                        self.max_retries + 1,
                        exc,
                    )
                    raise

                if attempt >= self.max_retries:
                    logger.error(
                        "All %d attempts exhausted. Last error: %s",
                        self.max_retries + 1,
                        exc,
                    )
                    raise

                delay = self.calculate_delay(attempt)
                logger.warning(
                    "Retry %d/%d after %.2fs – %s: %s",
                    attempt + 1,
                    self.max_retries,
                    delay,
                    type(exc).__name__,
                    exc,
                )
                time.sleep(delay)

        # last_exception is guaranteed to be set here because we only reach
        # this point if an exception was caught in the loop above.
        raise last_exception  # type: ignore[misc]

    def calculate_delay(self, attempt: int) -> float:
        """Return the back-off delay for the given *attempt* index.

        Uses the *full-jitter* algorithm::

            delay = random(0, min(max_delay, base_delay * base^attempt))

        This spreads retries across the full interval ``[0, cap]`` and
        avoids the *thundering-herd* problem.
        """
        exp_delay = self.base_delay * (self.exponential_base ** attempt)
        capped = min(exp_delay, self.max_delay)
        return random.uniform(0, capped)

    def should_retry(self, exception: Exception) -> bool:
        """Return ``True`` if *exception* is considered retryable.

        Retryable conditions:
        * Instance of :class:`ConnectionError` or :class:`TimeoutError`.
        * Exception message contains one of the keywords: ``rate_limit``,
          ``429``, ``503``, ``502``.

        Non-retryable conditions (checked first):
        * Instance of :class:`ValueError` or :class:`KeyError`.
        * Exception message contains ``authentication`` or ``unauthorized``
          (case-insensitive).
        """
        if isinstance(exception, _NON_RETRYABLE_TYPES):
            return False

        message_lower = str(exception).lower()
        if "authentication" in message_lower or "unauthorized" in message_lower:
            return False

        if isinstance(exception, (ConnectionError, TimeoutError)):
            return True

        for keyword in _RETRYABLE_KEYWORDS:
            if keyword in message_lower:
                return True

        return False


# ------------------------------------------------------------------
# Decorator API
# ------------------------------------------------------------------


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
) -> Callable[[F], F]:
    """Decorator that wraps a function with :class:`AIRetryStrategy`.

    Usage::

        @with_retry(max_retries=5, base_delay=0.5)
        def call_llm(prompt: str) -> str:
            ...
    """

    strategy = AIRetryStrategy(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
    )

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return strategy.execute(fn, *args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
