from __future__ import annotations

from typing import Any, Mapping

import httpx

from .agent_runner import BrowserAction
from .browser_approval import browser_action_binding
from .zworkforce_bridge import ZWorkforceBridge, ZWorkforceBridgeError


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
            {
                "status": status,
                "result_sha256": result_sha256,
                "error_code": error_code,
            },
            "browser effect finish",
        )
