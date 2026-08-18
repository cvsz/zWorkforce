from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import inspect
import ipaddress
import os
import socket
from typing import Any, Awaitable, Callable, Dict, Iterable, Mapping, Protocol, Sequence
from urllib.parse import urlsplit, urlunsplit


class BrowserPolicyError(ValueError):
    pass


class BrowserApprovalRequired(PermissionError):
    pass


class BrowserAutomationUnavailable(RuntimeError):
    pass


READ_ONLY_ACTIONS = frozenset({"navigate", "inspect", "screenshot", "extract"})
MUTATING_ACTIONS = frozenset({"click", "submit", "upload"})
ALL_ACTIONS = READ_ONLY_ACTIONS | MUTATING_ACTIONS


@dataclass(frozen=True)
class BrowserAction:
    kind: str
    url: str
    selector: str = ""
    value: str = ""
    artifact_id: str = ""
    idempotency_key: str = ""
    resolved_addresses: tuple[str, ...] = ()
    approval_task_id: str = ""


class BrowserExecutor(Protocol):
    enforces_resolved_addresses: bool

    async def execute(self, action: BrowserAction) -> Mapping[str, Any]: ...


ApprovalAuthorizer = Callable[[BrowserAction, str], bool | Awaitable[bool]]
HostResolver = Callable[[str], Iterable[str]]


def _default_resolver(hostname: str) -> Iterable[str]:
    addresses: set[str] = set()
    for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM):
        addresses.add(str(item[4][0]))
    return addresses


def _configured_hosts() -> tuple[str, ...]:
    raw = os.getenv("ZIDER_BROWSER_ALLOWED_HOSTS", "")
    return tuple(part.strip().lower().rstrip(".") for part in raw.split(",") if part.strip())


def _safe_url_metadata(raw_url: str) -> str:
    parsed = urlsplit(raw_url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class AgentRunner:
    """Policy boundary for Zider browser automation."""

    _executor: BrowserExecutor | None = None
    _approval_authorizer: ApprovalAuthorizer | None = None
    _allowed_hosts: tuple[str, ...] = _configured_hosts()
    _resolver: HostResolver = _default_resolver
    _timeout_seconds: int = 30
    _max_actions: int = 20

    @classmethod
    def configure(
        cls,
        *,
        executor: BrowserExecutor | None = None,
        approval_authorizer: ApprovalAuthorizer | None = None,
        allowed_hosts: Sequence[str] | None = None,
        resolver: HostResolver | None = None,
        timeout_seconds: int = 30,
        max_actions: int = 20,
    ) -> None:
        cls._executor = executor
        cls._approval_authorizer = approval_authorizer
        if allowed_hosts is not None:
            cls._allowed_hosts = tuple(
                str(host).strip().lower().rstrip(".") for host in allowed_hosts if str(host).strip()
            )
        if resolver is not None:
            cls._resolver = resolver
        cls._timeout_seconds = max(1, min(int(timeout_seconds), 120))
        cls._max_actions = max(1, min(int(max_actions), 50))

    @classmethod
    def reset(cls) -> None:
        cls._executor = None
        cls._approval_authorizer = None
        cls._allowed_hosts = _configured_hosts()
        cls._resolver = _default_resolver
        cls._timeout_seconds = 30
        cls._max_actions = 20

    @classmethod
    def _host_allowed(cls, hostname: str) -> bool:
        host = hostname.lower().rstrip(".")
        return any(host == allowed or host.endswith("." + allowed) for allowed in cls._allowed_hosts)

    @classmethod
    def _validate_url(cls, raw_url: str) -> tuple[str, tuple[str, ...]]:
        value = str(raw_url or "").strip()
        try:
            parsed = urlsplit(value)
        except ValueError as exc:
            raise BrowserPolicyError("browser action URL is invalid") from exc
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise BrowserPolicyError("browser actions require an http/https URL")
        if parsed.username is not None or parsed.password is not None:
            raise BrowserPolicyError("browser action URL must not contain credentials")
        hostname = parsed.hostname.lower().rstrip(".")
        if not cls._allowed_hosts or not cls._host_allowed(hostname):
            raise BrowserPolicyError("browser action host is not allowlisted")
        try:
            raw_addresses = tuple(cls._resolver(hostname))
        except OSError as exc:
            raise BrowserPolicyError("browser action host could not be resolved") from exc
        if not raw_addresses:
            raise BrowserPolicyError("browser action host did not resolve")
        addresses: list[str] = []
        for raw_address in raw_addresses:
            try:
                address = ipaddress.ip_address(raw_address)
            except ValueError as exc:
                raise BrowserPolicyError("browser action host resolved to an invalid address") from exc
            if not address.is_global:
                raise BrowserPolicyError("browser action host resolves to a non-public address")
            canonical = address.compressed
            if canonical not in addresses:
                addresses.append(canonical)
        canonical_url = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, parsed.query, ""))
        return canonical_url, tuple(sorted(addresses))

    @classmethod
    def _validate_action(cls, item: Mapping[str, Any]) -> BrowserAction:
        kind = str(item.get("kind") or "").strip().lower()
        if kind not in ALL_ACTIONS:
            raise BrowserPolicyError("unknown browser action")
        url, resolved_addresses = cls._validate_url(str(item.get("url") or ""))
        selector = str(item.get("selector") or "").strip()
        value = str(item.get("value") or "")
        artifact_id = str(item.get("artifact_id") or "").strip()
        idempotency_key = str(item.get("idempotency_key") or "").strip()
        if len(selector) > 1024 or len(value) > 4096 or len(artifact_id) > 256:
            raise BrowserPolicyError("browser action input exceeds configured bounds")
        if kind in {"click", "submit", "upload"} and not selector:
            raise BrowserPolicyError("mutating browser action requires a selector")
        if kind == "upload" and not artifact_id:
            raise BrowserPolicyError("upload requires an artifact_id, not a host file path")
        if kind in MUTATING_ACTIONS:
            if not idempotency_key or len(idempotency_key) > 128:
                raise BrowserPolicyError("mutating browser action requires a bounded idempotency_key")
        return BrowserAction(
            kind=kind,
            url=url,
            selector=selector,
            value=value,
            artifact_id=artifact_id,
            idempotency_key=idempotency_key,
            resolved_addresses=resolved_addresses,
        )

    @classmethod
    async def _authorize_mutation(cls, action: BrowserAction, approval_token: str) -> BrowserAction:
        if not approval_token or cls._approval_authorizer is None:
            raise BrowserApprovalRequired("mutating browser action requires explicit control-plane approval")
        decision = cls._approval_authorizer(action, approval_token)
        if inspect.isawaitable(decision):
            decision = await decision
        if decision is not True:
            raise BrowserApprovalRequired("mutating browser action approval was denied")
        return replace(action, approval_task_id=str(approval_token).strip())

    @classmethod
    def _require_pinned_executor(cls) -> BrowserExecutor:
        executor = cls._executor
        if executor is None:
            raise BrowserAutomationUnavailable("browser automation executor is not configured")
        if getattr(executor, "enforces_resolved_addresses", False) is not True:
            raise BrowserAutomationUnavailable("browser executor must enforce policy-validated resolved addresses")
        return executor

    @classmethod
    async def run_claw_task(
        cls,
        goal: str,
        model: str,
        *,
        actions: Sequence[Mapping[str, Any]] | None = None,
        approval_token: str = "",
    ) -> Dict[str, Any]:
        objective = str(goal or "").strip()
        if not objective or len(objective) > 4000:
            raise BrowserPolicyError("browser task goal must be between 1 and 4000 characters")
        requested = tuple(actions or ())
        if not requested:
            raise BrowserPolicyError("browser task requires explicit structured actions")
        if len(requested) > cls._max_actions:
            raise BrowserPolicyError("browser task exceeds the maximum action count")
        executor = cls._require_pinned_executor()

        validated = tuple(cls._validate_action(item) for item in requested)
        steps: list[dict[str, Any]] = []
        for index, original_action in enumerate(validated):
            action = original_action
            if action.kind in MUTATING_ACTIONS:
                action = await cls._authorize_mutation(action, approval_token)
            started_at = _utc_iso()
            try:
                result = await asyncio.wait_for(executor.execute(action), timeout=cls._timeout_seconds)
            except asyncio.TimeoutError as exc:
                raise BrowserAutomationUnavailable(
                    f"browser action timed out after {cls._timeout_seconds}s"
                ) from exc
            if not isinstance(result, Mapping):
                raise BrowserAutomationUnavailable("browser executor returned an invalid result")
            steps.append(
                {
                    "index": index,
                    "kind": action.kind,
                    "url": _safe_url_metadata(action.url),
                    "mutating": action.kind in MUTATING_ACTIONS,
                    "evidence": {
                        "idempotency_key": action.idempotency_key,
                        "approval_task_id": action.approval_task_id,
                        "artifact_id": action.artifact_id,
                        "effect_id": str(result.get("effect_id") or ""),
                        "result_sha256": str(result.get("result_sha256") or ""),
                        "redirect_count": int(result.get("redirect_count") or 0),
                        "browser_version": str(result.get("browser_version") or ""),
                        "started_at": started_at,
                        "finished_at": _utc_iso(),
                    },
                    "result": dict(result),
                }
            )

        return {"status": "completed", "goal": objective, "model": str(model or ""), "steps": steps}
