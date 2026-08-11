"""AI Middleware Pipeline for composable request/response processing.

Provides a priority-ordered middleware chain where each middleware can
inspect and modify the context dict before and after downstream processing.

Usage::

    pipeline = AIMiddlewarePipeline()
    pipeline.use(create_request_id_middleware(), name="request_id", priority=10)
    pipeline.use(create_logging_middleware(), name="logging", priority=20)
    pipeline.use(create_validation_middleware(max_prompt_length=4096), name="validation", priority=30)

    result = pipeline.execute({"prompt": "Hello, world!"})
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Type alias for a middleware callable.
# Signature: (context: Dict[str, Any], next_fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]
MiddlewareFn = Callable[[Dict[str, Any], Callable[[], Dict[str, Any]]], Dict[str, Any]]


class AIMiddlewarePipeline:
    """Composable middleware chain for AI request/response processing.

    Middleware functions are executed in ascending priority order (lower
    number runs first).  Each middleware receives the shared *context*
    dict and a *next_fn* that invokes the rest of the chain.

    If a middleware raises an exception the error is captured in the
    context under ``"error"`` and ``"error_source"``, and the remaining
    downstream middleware is skipped.
    """

    def __init__(self) -> None:
        """Initialise an empty middleware pipeline."""
        self._entries: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def use(
        self,
        middleware: MiddlewareFn,
        name: str = "",
        priority: int = 100,
    ) -> None:
        """Register a middleware with optional *name* and *priority*.

        Args:
            middleware: Callable with signature
                ``(context, next_fn) -> context``.
            name: Human-readable label used for logging and
                :meth:`remove`.  Defaults to the callable's
                ``__name__`` when empty.
            priority: Execution order — lower values run first.
        """
        resolved_name = name or getattr(middleware, "__name__", f"middleware_{len(self._entries)}")
        self._entries.append(
            {
                "middleware": middleware,
                "name": resolved_name,
                "priority": priority,
            }
        )
        self._entries.sort(key=lambda e: e["priority"])
        logger.debug("Registered middleware '%s' with priority %d", resolved_name, priority)

    def remove(self, name: str) -> None:
        """Remove the first middleware matching *name*.

        Args:
            name: The name assigned when the middleware was registered.

        Raises:
            KeyError: If no middleware with the given name exists.
        """
        for idx, entry in enumerate(self._entries):
            if entry["name"] == name:
                self._entries.pop(idx)
                logger.debug("Removed middleware '%s'", name)
                return
        raise KeyError(f"Middleware '{name}' not found in pipeline")

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run the full middleware pipeline against *context*.

        Args:
            context: Mutable dict shared across all middleware.

        Returns:
            The (potentially modified) context dict after the entire
            chain has executed.
        """
        if not self._entries:
            logger.warning("Executing empty middleware pipeline")
            return context

        ordered = list(self._entries)

        def build_chain(index: int) -> Callable[[], Dict[str, Any]]:
            """Recursively build the next-function chain."""
            if index >= len(ordered):
                return lambda: context

            entry = ordered[index]
            mw: MiddlewareFn = entry["middleware"]
            mw_name: str = entry["name"]

            def invoke() -> Dict[str, Any]:
                try:
                    return mw(context, build_chain(index + 1))
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Middleware '%s' raised %s: %s",
                        mw_name,
                        type(exc).__name__,
                        exc,
                    )
                    context["error"] = str(exc)
                    context["error_source"] = mw_name
                    return context

            return invoke

        build_chain(0)()
        return context

    def list_middleware(self) -> List[Dict[str, Any]]:
        """Return a list of registered middleware metadata.

        Each entry contains ``"name"`` and ``"priority"``.
        """
        return [
            {"name": entry["name"], "priority": entry["priority"]}
            for entry in self._entries
        ]


# ------------------------------------------------------------------
# Built-in middleware factories
# ------------------------------------------------------------------


def create_logging_middleware() -> MiddlewareFn:
    """Factory that returns a middleware logging request and response.

    Logs the incoming context keys before downstream processing and
    the presence of ``"error"`` after.
    """

    def logging_middleware(
        context: Dict[str, Any],
        next_fn: Callable[[], Dict[str, Any]],
    ) -> Dict[str, Any]:
        logger.info(
            "AI request  — keys: %s",
            sorted(context.keys()),
        )
        result = next_fn()
        if "error" in context:
            logger.error("AI response — error: %s", context["error"])
        else:
            logger.info("AI response — keys: %s", sorted(context.keys()))
        return result

    return logging_middleware


def create_timeout_middleware(timeout_seconds: float) -> MiddlewareFn:
    """Factory that adds timeout tracking metadata to the context.

    Sets ``"timeout_seconds"`` and ``"request_start_time"`` before
    downstream processing, and ``"elapsed_seconds"`` /
    ``"timeout_exceeded"`` after.

    Args:
        timeout_seconds: Maximum allowed processing time in seconds.
    """

    def timeout_middleware(
        context: Dict[str, Any],
        next_fn: Callable[[], Dict[str, Any]],
    ) -> Dict[str, Any]:
        start = time.monotonic()
        context["timeout_seconds"] = timeout_seconds
        context["request_start_time"] = start

        result = next_fn()

        elapsed = time.monotonic() - start
        context["elapsed_seconds"] = round(elapsed, 6)
        context["timeout_exceeded"] = elapsed > timeout_seconds
        if context["timeout_exceeded"]:
            logger.warning(
                "Request exceeded timeout: %.3fs > %.3fs",
                elapsed,
                timeout_seconds,
            )
        return result

    return timeout_middleware


def create_header_injection_middleware(headers: Dict[str, str]) -> MiddlewareFn:
    """Factory that injects custom headers into the context.

    Headers are merged into ``context["headers"]``, preserving any
    previously set values.

    Args:
        headers: Mapping of header names to values
            (e.g. ``{"CF-ZVEO-User": "zeaz-service"}``).
    """

    def header_injection_middleware(
        context: Dict[str, Any],
        next_fn: Callable[[], Dict[str, Any]],
    ) -> Dict[str, Any]:
        existing: Dict[str, str] = context.get("headers", {})
        existing.update(headers)
        context["headers"] = existing
        logger.debug("Injected headers: %s", list(headers.keys()))
        return next_fn()

    return header_injection_middleware


def create_request_id_middleware() -> MiddlewareFn:
    """Factory that generates a unique ``request_id`` via :func:`uuid.uuid4`.

    If a ``request_id`` is already present in the context it is left
    unchanged.
    """

    def request_id_middleware(
        context: Dict[str, Any],
        next_fn: Callable[[], Dict[str, Any]],
    ) -> Dict[str, Any]:
        if "request_id" not in context:
            context["request_id"] = str(uuid.uuid4())
            logger.debug("Generated request_id: %s", context["request_id"])
        return next_fn()

    return request_id_middleware


def create_validation_middleware(max_prompt_length: int) -> MiddlewareFn:
    """Factory that validates the prompt length in the context.

    Raises :class:`ValueError` (caught by the pipeline error handler)
    when ``context["prompt"]`` exceeds *max_prompt_length* characters.

    Args:
        max_prompt_length: Maximum allowed number of characters in the
            prompt string.
    """

    def validation_middleware(
        context: Dict[str, Any],
        next_fn: Callable[[], Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt: Optional[str] = context.get("prompt")
        if prompt is not None and len(prompt) > max_prompt_length:
            raise ValueError(
                f"Prompt length {len(prompt)} exceeds maximum "
                f"of {max_prompt_length} characters"
            )
        return next_fn()

    return validation_middleware
