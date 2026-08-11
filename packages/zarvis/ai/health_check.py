"""Provider health monitoring and circuit breaker module.

Implements the circuit breaker pattern for AI provider calls,
automatically isolating unhealthy providers and testing recovery.

State transitions:
    CLOSED  -> OPEN      : after ``failure_threshold`` consecutive failures
    OPEN    -> HALF_OPEN : after ``recovery_timeout`` seconds
    HALF_OPEN -> CLOSED  : after ``success_threshold`` consecutive successes
    HALF_OPEN -> OPEN    : on any single failure
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class CircuitState(enum.Enum):
    """Possible states for a circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class _ProviderCircuit:
    """Internal mutable state for a single provider's circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_successes: int = 0
    total_failures: int = 0
    last_failure_time: Optional[float] = None
    last_failure_error: Optional[str] = None
    opened_at: Optional[float] = None
    created_at: float = field(default_factory=time.monotonic)


class AIHealthMonitor:
    """Circuit breaker–based health monitor for AI providers.

    Args:
        failure_threshold: Consecutive failures before opening the circuit.
        recovery_timeout: Seconds to wait in OPEN before moving to HALF_OPEN.
        success_threshold: Consecutive successes in HALF_OPEN before closing.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 3,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be > 0")
        if success_threshold < 1:
            raise ValueError("success_threshold must be >= 1")

        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._success_threshold = success_threshold

        self._circuits: Dict[str, _ProviderCircuit] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create_circuit(self, provider: str) -> _ProviderCircuit:
        """Return the circuit for *provider*, creating one if needed.

        Must be called while holding ``self._lock``.
        """
        if provider not in self._circuits:
            self._circuits[provider] = _ProviderCircuit()
            logger.info("Registered new provider circuit: %s", provider)
        return self._circuits[provider]

    def _maybe_transition_to_half_open(self, circuit: _ProviderCircuit) -> None:
        """Move from OPEN → HALF_OPEN if the recovery timeout has elapsed.

        Must be called while holding ``self._lock``.
        """
        if circuit.state is not CircuitState.OPEN:
            return
        if circuit.opened_at is None:
            return
        if time.monotonic() - circuit.opened_at >= self._recovery_timeout:
            circuit.state = CircuitState.HALF_OPEN
            circuit.consecutive_successes = 0
            logger.info("Circuit transitioned OPEN -> HALF_OPEN")

    def _open_circuit(self, circuit: _ProviderCircuit, provider: str) -> None:
        """Transition the circuit to OPEN.

        Must be called while holding ``self._lock``.
        """
        circuit.state = CircuitState.OPEN
        circuit.opened_at = time.monotonic()
        circuit.consecutive_successes = 0
        logger.warning("Circuit OPENED for provider '%s'", provider)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_success(self, provider: str) -> None:
        """Record a successful call to *provider*.

        In HALF_OPEN, consecutive successes reaching
        ``success_threshold`` will close the circuit.
        """
        with self._lock:
            circuit = self._get_or_create_circuit(provider)
            self._maybe_transition_to_half_open(circuit)

            circuit.total_successes += 1
            circuit.consecutive_failures = 0
            circuit.consecutive_successes += 1

            if (
                circuit.state is CircuitState.HALF_OPEN
                and circuit.consecutive_successes >= self._success_threshold
            ):
                circuit.state = CircuitState.CLOSED
                circuit.opened_at = None
                logger.info(
                    "Circuit CLOSED for provider '%s' after recovery",
                    provider,
                )

    def record_failure(
        self, provider: str, error: Optional[str] = None
    ) -> None:
        """Record a failed call to *provider*.

        In CLOSED, consecutive failures reaching ``failure_threshold``
        will open the circuit.  In HALF_OPEN, any single failure
        re-opens the circuit.
        """
        now = time.monotonic()

        with self._lock:
            circuit = self._get_or_create_circuit(provider)
            self._maybe_transition_to_half_open(circuit)

            circuit.total_failures += 1
            circuit.consecutive_failures += 1
            circuit.consecutive_successes = 0
            circuit.last_failure_time = now
            circuit.last_failure_error = error

            if circuit.state is CircuitState.HALF_OPEN:
                self._open_circuit(circuit, provider)
                logger.warning(
                    "Provider '%s' failed during HALF_OPEN recovery",
                    provider,
                )
            elif (
                circuit.state is CircuitState.CLOSED
                and circuit.consecutive_failures >= self._failure_threshold
            ):
                self._open_circuit(circuit, provider)

    def is_healthy(self, provider: str) -> bool:
        """Return ``True`` if the provider's circuit allows requests.

        A provider is considered healthy when its circuit is CLOSED or
        HALF_OPEN (i.e. being tested for recovery).
        """
        with self._lock:
            circuit = self._get_or_create_circuit(provider)
            self._maybe_transition_to_half_open(circuit)
            return circuit.state is not CircuitState.OPEN

    def get_state(self, provider: str) -> str:
        """Return the current circuit state name for *provider*."""
        with self._lock:
            circuit = self._get_or_create_circuit(provider)
            self._maybe_transition_to_half_open(circuit)
            return circuit.state.value

    def get_health_report(self) -> Dict[str, Dict[str, object]]:
        """Return a health report covering every registered provider.

        Each entry contains:
        - ``state`` – current circuit state string
        - ``success_count`` – total successful calls
        - ``failure_count`` – total failed calls
        - ``last_failure_time`` – monotonic timestamp of last failure (or ``None``)
        - ``last_failure_error`` – error string of last failure (or ``None``)
        - ``uptime_percentage`` – success / total calls × 100 (0.0 if no calls)
        """
        report: Dict[str, Dict[str, object]] = {}

        with self._lock:
            for provider, circuit in self._circuits.items():
                self._maybe_transition_to_half_open(circuit)

                total = circuit.total_successes + circuit.total_failures
                uptime = (
                    (circuit.total_successes / total * 100.0)
                    if total > 0
                    else 0.0
                )

                report[provider] = {
                    "state": circuit.state.value,
                    "success_count": circuit.total_successes,
                    "failure_count": circuit.total_failures,
                    "last_failure_time": circuit.last_failure_time,
                    "last_failure_error": circuit.last_failure_error,
                    "uptime_percentage": round(uptime, 2),
                }

        return report

    def get_healthy_providers(self) -> List[str]:
        """Return a list of providers whose circuits are CLOSED."""
        with self._lock:
            healthy: List[str] = []
            for provider, circuit in self._circuits.items():
                self._maybe_transition_to_half_open(circuit)
                if circuit.state is CircuitState.CLOSED:
                    healthy.append(provider)
            return healthy

    def reset(self, provider: str) -> None:
        """Force-reset *provider*'s circuit to CLOSED."""
        with self._lock:
            circuit = self._get_or_create_circuit(provider)
            circuit.state = CircuitState.CLOSED
            circuit.consecutive_failures = 0
            circuit.consecutive_successes = 0
            circuit.opened_at = None
            logger.info("Circuit manually reset for provider '%s'", provider)

    def reset_all(self) -> None:
        """Force-reset every registered circuit to CLOSED."""
        with self._lock:
            for provider in list(self._circuits):
                circuit = self._circuits[provider]
                circuit.state = CircuitState.CLOSED
                circuit.consecutive_failures = 0
                circuit.consecutive_successes = 0
                circuit.opened_at = None
            logger.info("All circuits manually reset")
