from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any, Mapping, Protocol
from urllib.parse import urlsplit, urlunsplit

from .agent_runner import BrowserAction
from .zworkforce_bridge import ZWorkforceBridge, ZWorkforceBridgeError


_APPROVAL_PREFIX = "zider-browser-approval:v1 "
_TASK_ID_RE = re.compile(r"^[0-9a-fA-F-]{36}$")
_ALLOWED_TASK_STATES = frozenset({"queued", "running", "succeeded"})


class BrowserApprovalBridge(Protocol):
    @classmethod
    async def get_agents(cls) -> list[Mapping[str, Any]]: ...

    @classmethod
    async def request_browser_approval(
        cls,
        *,
        agent_id: str,
        prompt: str,
        idempotency_key: str,
    ) -> Mapping[str, Any]: ...

    @classmethod
    async def get_task(cls, task_id: str) -> Mapping[str, Any]: ...

    @classmethod
    async def get_task_approvals(cls, task_id: str) -> list[Mapping[str, Any]]: ...

    @classmethod
    async def cancel_task(cls, task_id: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class BrowserApprovalEnvelope:
    binding_sha256: str
    kind: str
    safe_destination: str
    expires_at: str

    def prompt(self) -> str:
        return _APPROVAL_PREFIX + json.dumps(
            {
                "binding_sha256": self.binding_sha256,
                "kind": self.kind,
                "safe_destination": self.safe_destination,
                "expires_at": self.expires_at,
            },
            sort_keys=True,
            separators=(",", ":"),
        )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_destination(raw_url: str) -> str:
    parsed = urlsplit(raw_url)
    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    try:
        port = parsed.port
    except ValueError:
        port = None
    authority = host if port is None else f"{host}:{port}"
    return urlunsplit((parsed.scheme, authority, parsed.path, "", ""))


def browser_action_binding(action: BrowserAction) -> str:
    """Return a secret-safe digest binding one approval to exactly one action."""

    material = {
        "kind": action.kind,
        "destination_sha256": _sha256(action.url),
        "selector_sha256": _sha256(action.selector),
        "value_sha256": _sha256(action.value),
        "artifact_id_sha256": _sha256(action.artifact_id),
        "idempotency_key": action.idempotency_key,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return _sha256(encoded)


def _parse_timestamp(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_prompt(prompt: Any) -> BrowserApprovalEnvelope | None:
    raw = str(prompt or "")
    if not raw.startswith(_APPROVAL_PREFIX):
        return None
    try:
        payload = json.loads(raw[len(_APPROVAL_PREFIX) :])
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    binding = str(payload.get("binding_sha256") or "")
    kind = str(payload.get("kind") or "")
    safe_destination = str(payload.get("safe_destination") or "")
    expires_at = str(payload.get("expires_at") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", binding):
        return None
    if not kind or not safe_destination or _parse_timestamp(expires_at) is None:
        return None
    return BrowserApprovalEnvelope(binding, kind, safe_destination, expires_at)


class ZWorkforceMutationApprovalAdapter:
    """Validate browser mutations against durable zWorkforce task approvals.

    zWorkforce remains the approval authority. Zider stores no approval decision
    locally. Approval request tasks are accepted only when the configured agent
    is enabled, requires mutation approval, and has no tools or skills, so the
    approval carrier cannot itself perform external side effects after approval.
    The task prompt stores only hashes of sensitive action fields plus a sanitized
    destination.
    """

    def __init__(
        self,
        *,
        bridge: type[BrowserApprovalBridge] = ZWorkforceBridge,
        ttl_seconds: int = 600,
        now=None,
    ) -> None:
        self.bridge = bridge
        self.ttl_seconds = max(60, min(int(ttl_seconds), 3600))
        self._now = now or (lambda: datetime.now(timezone.utc))

    def envelope(self, action: BrowserAction) -> BrowserApprovalEnvelope:
        expires = self._now().astimezone(timezone.utc) + timedelta(seconds=self.ttl_seconds)
        return BrowserApprovalEnvelope(
            binding_sha256=browser_action_binding(action),
            kind=action.kind,
            safe_destination=_safe_destination(action.url),
            expires_at=expires.isoformat(timespec="seconds"),
        )

    async def _require_safe_approval_agent(self, agent_id: str) -> Mapping[str, Any]:
        target = str(agent_id or "").strip()
        if not target:
            raise ZWorkforceBridgeError("browser approval agent id is required", status_code=400)
        agents = await self.bridge.get_agents()
        agent = next((item for item in agents if str(item.get("id") or "") == target), None)
        if not agent or not bool(agent.get("enabled")):
            raise ZWorkforceBridgeError("configured browser approval agent is unavailable")
        if not bool(agent.get("requires_approval_for_mutations")) or int(agent.get("required_approvals") or 0) < 1:
            raise ZWorkforceBridgeError("configured browser approval agent does not require mutation approval")
        if list(agent.get("allowed_tools") or []) or list(agent.get("skill_ids") or []):
            raise ZWorkforceBridgeError("browser approval agent must not have tools or skills")
        return agent

    async def request(self, action: BrowserAction, *, agent_id: str) -> Mapping[str, Any]:
        if not action.idempotency_key:
            raise ValueError("browser mutation approval requires an idempotency key")
        await self._require_safe_approval_agent(agent_id)
        envelope = self.envelope(action)
        approval_key = "browser-approval:" + _sha256(action.idempotency_key)[:48]
        task = await self.bridge.request_browser_approval(
            agent_id=str(agent_id).strip(),
            prompt=envelope.prompt(),
            idempotency_key=approval_key,
        )
        if str(task.get("status") or "") != "waiting_approval" or int(task.get("required_approvals") or 0) < 1:
            task_id = str(task.get("id") or "")
            if task_id:
                try:
                    await self.bridge.cancel_task(task_id)
                except Exception:
                    pass
            raise ZWorkforceBridgeError(
                "configured zWorkforce browser approval agent does not enforce mutation approval"
            )
        return task

    async def authorize(self, action: BrowserAction, approval_token: str) -> bool:
        task_id = str(approval_token or "").strip()
        if not _TASK_ID_RE.fullmatch(task_id):
            return False
        try:
            task = await self.bridge.get_task(task_id)
            approvals = await self.bridge.get_task_approvals(task_id)
        except (ZWorkforceBridgeError, OSError, ValueError, TypeError):
            return False

        if not bool(task.get("mutating")):
            return False
        if bool(task.get("cancel_requested")):
            return False
        if str(task.get("status") or "") not in _ALLOWED_TASK_STATES:
            return False
        required = int(task.get("required_approvals") or 0)
        if required < 1:
            return False
        approved_at = _parse_timestamp(task.get("approved_at"))
        if approved_at is None:
            return False
        now = self._now().astimezone(timezone.utc)
        if approved_at > now:
            return False
        if not str(task.get("created_by") or "").strip():
            return False

        envelope = _parse_prompt(task.get("prompt"))
        if envelope is None:
            return False
        if envelope.kind != action.kind:
            return False
        if envelope.binding_sha256 != browser_action_binding(action):
            return False
        if envelope.safe_destination != _safe_destination(action.url):
            return False
        expires_at = _parse_timestamp(envelope.expires_at)
        if expires_at is None or approved_at > expires_at or now > expires_at:
            return False

        if any(str(item.get("decision") or "") == "reject" for item in approvals):
            return False
        approved_actors = {
            str(item.get("actor") or "").strip()
            for item in approvals
            if str(item.get("decision") or "") == "approve" and str(item.get("actor") or "").strip()
        }
        return len(approved_actors) >= required
