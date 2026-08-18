from __future__ import annotations

import asyncio
from dataclasses import replace
import ipaddress
from typing import Callable, Mapping, Protocol
from urllib.parse import urlsplit

from .agent_runner import BrowserAction, BrowserAutomationUnavailable, BrowserPolicyError, MUTATING_ACTIONS


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


RedirectValidator = Callable[[str], tuple[str, tuple[str, ...]]]


class PinnedBrowserExecutor:
    """Execute only against policy-validated public destination addresses.

    Redirects are never followed by the transport. Read-only redirects are fed
    back through the same AgentRunner URL policy, DNS resolution, and public-IP
    checks before a new pinned request is made. Redirects triggered by a browser
    mutation remain fail-closed until durable side-effect reconciliation lands;
    replaying the mutation merely to follow a redirect would be unsafe.
    """

    enforces_resolved_addresses = True

    def __init__(
        self,
        transport: BrowserTransport,
        *,
        timeout_seconds: int = 30,
        redirect_validator: RedirectValidator | None = None,
        max_redirects: int = 5,
    ) -> None:
        self.transport = transport
        self.timeout_seconds = max(1, min(int(timeout_seconds), 120))
        self.redirect_validator = redirect_validator
        self.max_redirects = max(0, min(int(max_redirects), 10))

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

    @staticmethod
    def _origin_authority(action: BrowserAction) -> tuple[str, str]:
        parsed = urlsplit(action.url)
        host = parsed.hostname or ""
        if not host:
            raise BrowserPolicyError("browser action URL is missing a hostname")
        try:
            port = parsed.port
        except ValueError as exc:
            raise BrowserPolicyError("browser action URL contains an invalid port") from exc
        default_port = 443 if parsed.scheme == "https" else 80
        bracketed = f"[{host}]" if ":" in host else host
        if port is None or port == default_port:
            return bracketed, host
        return f"{bracketed}:{port}", host

    async def _execute_once(self, action: BrowserAction) -> Mapping[str, object]:
        host_header, tls_server_name = self._origin_authority(action)
        last_error: Exception | None = None
        for connect_ip in self._addresses(action):
            try:
                result = await asyncio.wait_for(
                    self.transport.request(
                        action=action,
                        connect_ip=connect_ip,
                        host_header=host_header,
                        tls_server_name=tls_server_name,
                        timeout_seconds=self.timeout_seconds,
                    ),
                    timeout=self.timeout_seconds,
                )
            except (asyncio.TimeoutError, OSError) as exc:
                last_error = exc
                continue
            if not isinstance(result, Mapping):
                raise BrowserAutomationUnavailable("browser transport returned an invalid result")
            return dict(result)
        raise BrowserAutomationUnavailable(
            "browser transport could not connect to an approved destination"
        ) from last_error

    async def execute(self, action: BrowserAction) -> Mapping[str, object]:
        self._require_transport_contract()
        current = action
        redirects = 0

        while True:
            result = dict(await self._execute_once(current))
            redirect_url = str(result.get("redirect_url") or "").strip()
            if not redirect_url:
                if redirects:
                    result["redirect_count"] = redirects
                return result

            if current.kind in MUTATING_ACTIONS:
                raise BrowserPolicyError(
                    "browser mutation redirect was blocked; side-effect reconciliation is required before following"
                )
            if self.redirect_validator is None:
                raise BrowserPolicyError("browser redirects require policy revalidation before following")
            if redirects >= self.max_redirects:
                raise BrowserPolicyError("browser redirect limit exceeded")

            validated_url, addresses = self.redirect_validator(redirect_url)
            if not addresses:
                raise BrowserPolicyError("browser redirect did not produce policy-validated pinned addresses")
            current = replace(current, url=validated_url, resolved_addresses=tuple(addresses))
            redirects += 1
