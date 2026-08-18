from __future__ import annotations

import hashlib
import json
from typing import Any, Awaitable, Callable, Mapping, Protocol

import httpx

from .agent_runner import BrowserAction, BrowserAutomationUnavailable, MUTATING_ACTIONS
from .browser_approval import browser_action_binding
from .zworkforce_bridge import ZWorkforceBridge, ZWorkforceBridgeError


class BrowserEffectDelegate(Protocol):
    enforces_resolved_addresses: bool

    async def execute(self, action: BrowserAction) -> Mapping[str, Any]: ...


CancelChecker = Callable[[BrowserAction], Awaitable[bool]]


class ZWorkforceBrowserEffectController:
    """Drive durable browser-effect lifecycle through the authenticated zWorkforce API."""

    timeout_seconds = 8.0

    @classmethod
    async def _post(cls, path: str, payload: Mapping[str, Any], operation: str) -> dict[str, Any]:
        base_url = ZWorkforceBridge._base_url()
        try:
            async with httpx.AsyncClient(timeout=cls.timeout_seconds) as client:
                response = await client.post(
                    f"{base_url}{path}",
                    json=dict(payload),
                    headers=ZWorkforceBridge._headers(),
                )
        except httpx.RequestError as exc:
            raise ZWorkforceBridgeError("zWorkforce control plane is unavailable") from exc
        ZWorkforceBridge._raise_for_status(response, operation)
        return ZWorkforceBridge._decode_json(response, operation)

    async def begin(self, action: BrowserAction, approval_task_id: str) -> dict[str, Any]:
        return await self._post(
            "/api/v1/browser-effects",
            {
                "idempotency_key": action.idempotency_key,
                "action_sha256": browser_action_binding(action),
                "approval_task_id": approval_task_id,
            },
            "browser effect begin",
        )

    async def claim(self, effect_id: str) -> tuple[dict[str, Any], bool]:
        payload = await self._post(
            f"/api/v1/browser-effects/{effect_id}/claim",
            {},
            "browser effect claim",
        )
        effect = payload.get("effect")
        if not isinstance(effect, dict) or not isinstance(payload.get("claimed"), bool):
            raise ZWorkforceBridgeError("zWorkforce browser effect claim returned an invalid response shape", status_code=502)
        return dict(effect), bool(payload["claimed"])

    async def finish(
        self,
        effect_id: str,
        *,
        status: str,
        result_sha256: str = "",
        error_code: str = "",
    ) -> dict[str, Any]:
        return await self._post(
            f"/api/v1/browser-effects/{effect_id}/finish",
            {"status": status, "result_sha256": result_sha256, "error_code": error_code},
            "browser effect finish",
        )


class DurableBrowserEffectExecutor:
    """Fence every mutating browser action through the durable control-plane ledger."""

    enforces_resolved_addresses = True

    def __init__(
        self,
        delegate: BrowserEffectDelegate,
        controller: ZWorkforceBrowserEffectController | None = None,
        cancel_checker: CancelChecker | None = None,
    ) -> None:
        if getattr(delegate, "enforces_resolved_addresses", False) is not True:
            raise BrowserAutomationUnavailable("browser effect delegate must enforce resolved addresses")
        self.delegate = delegate
        self.controller = controller or ZWorkforceBrowserEffectController()
        self.cancel_checker = cancel_checker

    @staticmethod
    def _result_digest(result: Mapping[str, Any]) -> str:
        encoded = json.dumps(dict(result), sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    async def _best_effort_unknown(self, effect_id: str, error_code: str) -> None:
        try:
            await self.controller.finish(effect_id, status="unknown", error_code=error_code)
        except Exception:
            pass

    async def execute(self, action: BrowserAction) -> Mapping[str, Any]:
        if action.kind not in MUTATING_ACTIONS:
            return await self.delegate.execute(action)
        if not action.approval_task_id:
            raise BrowserAutomationUnavailable("browser mutation is missing its durable approval task binding")

        effect = await self.controller.begin(action, action.approval_task_id)
        effect_id = str(effect.get("id") or "")
        status = str(effect.get("status") or "")
        if not effect_id:
            raise BrowserAutomationUnavailable("browser effect begin returned an invalid effect")
        if status == "succeeded":
            return {"ok": True, "deduplicated": True, "effect_id": effect_id, "result_sha256": effect.get("result_sha256", "")}
        if status in {"executing", "unknown"}:
            raise BrowserAutomationUnavailable("browser effect requires reconciliation before retry")
        if status in {"failed", "canceled"}:
            raise BrowserAutomationUnavailable("browser effect is terminal and cannot be replayed")

        claimed_effect, claimed = await self.controller.claim(effect_id)
        if not claimed or str(claimed_effect.get("status") or "") != "executing":
            raise BrowserAutomationUnavailable("browser effect could not be atomically claimed")
        try:
            result = await self.delegate.execute(action)
        except Exception:
            await self._best_effort_unknown(effect_id, "execution_ambiguous")
            raise
        if not isinstance(result, Mapping):
            await self._best_effort_unknown(effect_id, "invalid_result")
            raise BrowserAutomationUnavailable("browser executor returned an invalid result")
        if self.cancel_checker is not None:
            try:
                canceled = await self.cancel_checker(action)
            except Exception:
                canceled = False
            if canceled:
                await self._best_effort_unknown(effect_id, "canceled_during_execution")
                raise BrowserAutomationUnavailable(
                    "browser mutation result is ambiguous: the approval task was canceled during execution"
                )
        digest = self._result_digest(result)
        try:
            await self.controller.finish(effect_id, status="succeeded", result_sha256=digest)
        except Exception:
            await self._best_effort_unknown(effect_id, "completion_ambiguous")
            raise
        return {**dict(result), "effect_id": effect_id, "result_sha256": digest}
