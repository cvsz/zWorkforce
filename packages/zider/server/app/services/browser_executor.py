from __future__ import annotations

import asyncio
import ipaddress
from typing import Mapping, Protocol
from urllib.parse import urlsplit

from .agent_runner import BrowserAction, BrowserAutomationUnavailable, BrowserPolicyError


class BrowserTransport(Protocol):
    async def request(self, *, action: BrowserAction, connect_ip: str, host_header: str, timeout_seconds: int) -> Mapping[str, object]: ...


class PinnedBrowserExecutor:
    """Execute only against policy-validated public destination addresses."""

    enforces_resolved_addresses = True

    def __init__(self, transport: BrowserTransport, *, timeout_seconds: int = 30) -> None:
        self.transport = transport
        self.timeout_seconds = max(1, min(int(timeout_seconds), 120))

    @staticmethod
    def _addresses(action: BrowserAction) -> tuple[str, ...]:
        values: list[str] = []
        for raw in action.resolved_addresses:
            try:
                address = ipaddress.ip_address(raw)
            except ValueError as exc:
                raise BrowserPolicyError("browser action contains an invalid pinned address") from exc
            if not address.is_global:
                raise BrowserPolicyError("browser action pinned address must be public")
            canonical = address.compressed
            if canonical not in values:
                values.append(canonical)
        if not values:
            raise BrowserPolicyError("browser action requires policy-validated pinned addresses")
        return tuple(values)

    async def execute(self, action: BrowserAction) -> Mapping[str, object]:
        host = urlsplit(action.url).hostname or ""
        if not host:
            raise BrowserPolicyError("browser action URL is missing a hostname")
        last_error: Exception | None = None
        for connect_ip in self._addresses(action):
            try:
                result = await asyncio.wait_for(
                    self.transport.request(
                        action=action,
                        connect_ip=connect_ip,
                        host_header=host,
                        timeout_seconds=self.timeout_seconds,
                    ),
                    timeout=self.timeout_seconds,
                )
            except (asyncio.TimeoutError, OSError) as exc:
                last_error = exc
                continue
            if not isinstance(result, Mapping):
                raise BrowserAutomationUnavailable("browser transport returned an invalid result")
            if result.get("redirect_url"):
                raise BrowserPolicyError("browser redirects require policy revalidation before following")
            return dict(result)
        raise BrowserAutomationUnavailable("browser transport could not connect to an approved destination") from last_error
