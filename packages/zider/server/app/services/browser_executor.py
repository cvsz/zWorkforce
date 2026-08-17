from __future__ import annotations

import asyncio
import ipaddress
from typing import Mapping, Protocol
from urllib.parse import urlsplit

from .agent_runner import BrowserAction, BrowserAutomationUnavailable, BrowserPolicyError


class BrowserTransport(Protocol):
    enforces_pinned_destination: bool
    disables_automatic_redirects: bool
    verifies_tls_server_identity: bool

    async def request(
        self,
        *,
        action: BrowserAction,
        connect_ip: str,
        host_header: str,
        tls_server_name: str,
        timeout_seconds: int,
    ) -> Mapping[str, object]: ...


class PinnedBrowserExecutor:
    """Execute only against policy-validated public destination addresses."""

    enforces_resolved_addresses = True

    def __init__(self, transport: BrowserTransport, *, timeout_seconds: int = 30) -> None:
        self.transport = transport
        self.timeout_seconds = max(1, min(int(timeout_seconds), 120))

    def _require_transport_contract(self) -> None:
        if getattr(self.transport, "enforces_pinned_destination", False) is not True:
            raise BrowserAutomationUnavailable(
                "browser transport must enforce the supplied pinned destination"
            )
        if getattr(self.transport, "disables_automatic_redirects", False) is not True:
            raise BrowserAutomationUnavailable(
                "browser transport must disable automatic redirects"
            )
        if getattr(self.transport, "verifies_tls_server_identity", False) is not True:
            raise BrowserAutomationUnavailable(
                "browser transport must verify TLS against the original hostname"
            )

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
        self._require_transport_contract()
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
                        tls_server_name=host,
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
        raise BrowserAutomationUnavailable(
            "browser transport could not connect to an approved destination"
        ) from last_error
