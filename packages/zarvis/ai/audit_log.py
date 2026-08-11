"""Structured audit logging system for AI operations.

Provides compliance-grade, thread-safe audit logging with an in-memory
ring buffer, queryable entries, and JSON export capabilities.
"""

import json
import logging
import threading
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Supported severity levels for audit log entries."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AIAuditLogger:
    """Records all AI operations for compliance and debugging.

    Uses a fixed-size ring buffer to cap memory usage while retaining
    the most recent entries.  Every public method is thread-safe.

    Args:
        max_entries: Maximum number of log entries kept in memory.
    """

    _VALID_SEVERITIES = frozenset(s.value for s in Severity)

    def __init__(self, max_entries: int = 10000) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        self._buffer: deque[Dict[str, Any]] = deque(maxlen=max_entries)
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {
            "total_requests": 0,
            "total_responses": 0,
            "total_errors": 0,
            "total_security_events": 0,
        }
        logger.info("AIAuditLogger initialised with max_entries=%d", max_entries)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now_iso() -> str:
        """Return the current UTC time as an ISO-8601 string."""
        return datetime.now(timezone.utc).isoformat()

    def _append(self, entry: Dict[str, Any]) -> None:
        """Append *entry* to the ring buffer (caller must hold lock)."""
        self._buffer.append(entry)

    @staticmethod
    def _validate_severity(severity: str) -> str:
        """Normalise and validate a severity string."""
        normalised = severity.upper()
        if normalised not in AIAuditLogger._VALID_SEVERITIES:
            raise ValueError(
                f"Invalid severity '{severity}'. "
                f"Must be one of {sorted(AIAuditLogger._VALID_SEVERITIES)}"
            )
        return normalised

    # ------------------------------------------------------------------
    # Public logging methods
    # ------------------------------------------------------------------

    def log_request(
        self,
        request_id: str,
        provider: str,
        prompt_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an incoming AI request.

        Args:
            request_id: Unique identifier for the request.
            provider:   AI provider name (e.g. ``"openai"``).
            prompt_id:  Identifier of the prompt template used.
            user_id:    Identifier of the requesting user.
            metadata:   Arbitrary extra data attached to the entry.
        """
        entry: Dict[str, Any] = {
            "timestamp": self._now_iso(),
            "request_id": request_id,
            "event_type": "request",
            "provider": provider,
            "prompt_id": prompt_id,
            "user_id": user_id,
            "severity": Severity.INFO.value,
            "metadata": metadata or {},
        }
        with self._lock:
            self._append(entry)
            self._counters["total_requests"] += 1
        logger.debug("Logged request %s from user %s", request_id, user_id)

    def log_response(
        self,
        request_id: str,
        provider: str,
        status: str,
        latency: float,
        token_count: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an AI provider response.

        Args:
            request_id:  Unique identifier for the original request.
            provider:    AI provider name.
            status:      Response status (e.g. ``"success"``, ``"failure"``).
            latency:     Round-trip time in seconds.
            token_count: Number of tokens consumed.
            metadata:    Arbitrary extra data attached to the entry.
        """
        entry: Dict[str, Any] = {
            "timestamp": self._now_iso(),
            "request_id": request_id,
            "event_type": "response",
            "provider": provider,
            "status": status,
            "latency": latency,
            "token_count": token_count,
            "severity": Severity.INFO.value,
            "metadata": metadata or {},
        }
        with self._lock:
            self._append(entry)
            self._counters["total_responses"] += 1
        logger.debug("Logged response for %s — status=%s", request_id, status)

    def log_security_event(
        self,
        event_type: str,
        details: str,
        severity: str,
        request_id: Optional[str] = None,
    ) -> None:
        """Log a security-related event.

        Use this for guardrail triggers, prompt-injection attempts,
        policy violations, and similar events.

        Args:
            event_type: Category of the security event
                        (e.g. ``"injection_attempt"``).
            details:    Human-readable description.
            severity:   One of ``INFO``, ``WARNING``, ``ERROR``,
                        ``CRITICAL``.
            request_id: Optional related request identifier.
        """
        validated_severity = self._validate_severity(severity)
        entry: Dict[str, Any] = {
            "timestamp": self._now_iso(),
            "request_id": request_id,
            "event_type": "security",
            "security_event_type": event_type,
            "details": details,
            "severity": validated_severity,
        }
        with self._lock:
            self._append(entry)
            self._counters["total_security_events"] += 1
        logger.warning(
            "Security event [%s] severity=%s: %s",
            event_type,
            validated_severity,
            details,
        )

    def log_error(
        self,
        request_id: str,
        provider: str,
        error_type: str,
        error_message: str,
    ) -> None:
        """Log an error that occurred during AI processing.

        Args:
            request_id:    Unique identifier for the original request.
            provider:      AI provider name.
            error_type:    Programmatic error category
                           (e.g. ``"timeout"``, ``"rate_limit"``).
            error_message: Human-readable error description.
        """
        entry: Dict[str, Any] = {
            "timestamp": self._now_iso(),
            "request_id": request_id,
            "event_type": "error",
            "provider": provider,
            "error_type": error_type,
            "error_message": error_message,
            "severity": Severity.ERROR.value,
        }
        with self._lock:
            self._append(entry)
            self._counters["total_errors"] += 1
        logger.error(
            "Error for %s [%s]: %s", request_id, error_type, error_message
        )

    # ------------------------------------------------------------------
    # Query & reporting
    # ------------------------------------------------------------------

    def query(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query log entries with optional filters.

        Supported filter keys:

        * ``provider``  — exact match on provider name.
        * ``user_id``   — exact match on user identifier.
        * ``status``    — exact match on response status.
        * ``event_type``— exact match on event type.
        * ``severity``  — exact match on severity level.
        * ``request_id``— exact match on request identifier.
        * ``time_from`` — ISO-8601 string; entries *on or after* this
          timestamp.
        * ``time_to``   — ISO-8601 string; entries *on or before* this
          timestamp.

        Args:
            filters: Dictionary of filter criteria.
            limit:   Maximum number of entries to return.

        Returns:
            Matching entries in reverse-chronological order.
        """
        filters = filters or {}
        time_from = filters.get("time_from")
        time_to = filters.get("time_to")

        # Pre-parse time boundaries once
        parsed_from = (
            datetime.fromisoformat(time_from) if time_from else None
        )
        parsed_to = (
            datetime.fromisoformat(time_to) if time_to else None
        )

        # Simple-equality keys
        eq_keys = {
            k: v
            for k, v in filters.items()
            if k not in ("time_from", "time_to")
        }

        results: List[Dict[str, Any]] = []
        with self._lock:
            for entry in reversed(self._buffer):
                if len(results) >= limit:
                    break
                if not self._matches(entry, eq_keys, parsed_from, parsed_to):
                    continue
                results.append(entry.copy())
        return results

    @staticmethod
    def _matches(
        entry: Dict[str, Any],
        eq_keys: Dict[str, Any],
        time_from: Optional[datetime],
        time_to: Optional[datetime],
    ) -> bool:
        """Return ``True`` if *entry* satisfies all filter criteria."""
        for key, value in eq_keys.items():
            if entry.get(key) != value:
                return False

        if time_from or time_to:
            entry_time = datetime.fromisoformat(entry["timestamp"])
            if time_from and entry_time < time_from:
                return False
            if time_to and entry_time > time_to:
                return False

        return True

    def get_summary(self) -> Dict[str, Any]:
        """Return aggregate statistics over the current buffer.

        Returns:
            Dictionary containing:

            * ``total_requests``        — lifetime request count.
            * ``total_responses``       — lifetime response count.
            * ``total_errors``          — lifetime error count.
            * ``total_security_events`` — lifetime security event count.
            * ``error_rate``            — errors / requests (0.0 if none).
            * ``buffer_size``           — current number of buffered entries.
            * ``top_providers``         — provider → request count mapping.
            * ``avg_latency``           — mean latency across responses.
        """
        with self._lock:
            provider_counts: Dict[str, int] = {}
            total_latency = 0.0
            response_count = 0

            for entry in self._buffer:
                if entry["event_type"] == "request":
                    provider = entry.get("provider", "unknown")
                    provider_counts[provider] = (
                        provider_counts.get(provider, 0) + 1
                    )
                elif entry["event_type"] == "response":
                    total_latency += entry.get("latency", 0.0)
                    response_count += 1

            total_requests = self._counters["total_requests"]
            total_errors = self._counters["total_errors"]

            return {
                "total_requests": total_requests,
                "total_responses": self._counters["total_responses"],
                "total_errors": total_errors,
                "total_security_events": self._counters[
                    "total_security_events"
                ],
                "error_rate": (
                    total_errors / total_requests if total_requests else 0.0
                ),
                "buffer_size": len(self._buffer),
                "top_providers": dict(
                    sorted(
                        provider_counts.items(),
                        key=lambda item: item[1],
                        reverse=True,
                    )
                ),
                "avg_latency": (
                    total_latency / response_count
                    if response_count
                    else 0.0
                ),
            }

    def export_json(self) -> str:
        """Export all buffered log entries as a JSON string.

        Returns:
            A JSON-encoded string of all entries in chronological order.
        """
        with self._lock:
            entries = list(self._buffer)
        return json.dumps(entries, ensure_ascii=False, indent=2)
