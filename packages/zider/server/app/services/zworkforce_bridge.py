from __future__ import annotations

import os
from typing import Any, Dict
from urllib.parse import urlsplit

import httpx


class ZWorkforceBridgeError(RuntimeError):
    """Bounded public error for control-plane bridge failures."""

    def __init__(self, message: str, *, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


class ZWorkforceBridge:
    """Bridge connecting Zider to the zWorkforce control plane.

    The bridge never fabricates successful control-plane state. Network errors,
    authentication failures, non-success upstream responses, and malformed JSON
    fail closed with bounded messages that do not reflect upstream bodies or
    credentials. Bearer credentials are sent over HTTPS except for explicit
    loopback development endpoints.
    """

    ZWF_URL = os.getenv("ZWORKFORCE_API_URL", "http://127.0.0.1:8000").rstrip("/")
    ZWF_TOKEN = os.getenv("ZWORKFORCE_API_KEY", "")
    OVERVIEW_TIMEOUT_SECONDS = 5.0
    DISPATCH_TIMEOUT_SECONDS = 8.0

    @classmethod
    def _headers(cls) -> Dict[str, str]:
        return {"Authorization": f"Bearer {cls.ZWF_TOKEN}"} if cls.ZWF_TOKEN else {}

    @classmethod
    def _base_url(cls) -> str:
        value = str(cls.ZWF_URL or "").strip().rstrip("/")
        try:
            parsed = urlsplit(value)
        except ValueError as exc:
            raise ZWorkforceBridgeError("zWorkforce API URL is invalid") from exc
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ZWorkforceBridgeError("zWorkforce API URL must be http or https")
        if parsed.username is not None or parsed.password is not None:
            raise ZWorkforceBridgeError("zWorkforce API URL must not contain credentials")
        host = parsed.hostname.lower().rstrip(".")
        loopback = host in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not loopback:
            raise ZWorkforceBridgeError("zWorkforce API URL must use HTTPS outside loopback")
        return value

    @staticmethod
    def _decode_json(resp: httpx.Response, operation: str) -> Dict[str, Any]:
        try:
            payload = resp.json()
        except ValueError as exc:
            raise ZWorkforceBridgeError(
                f"zWorkforce {operation} returned invalid JSON",
                status_code=502,
            ) from exc
        if not isinstance(payload, dict):
            raise ZWorkforceBridgeError(
                f"zWorkforce {operation} returned an invalid response shape",
                status_code=502,
            )
        return payload

    @staticmethod
    def _raise_for_status(resp: httpx.Response, operation: str) -> None:
        if 200 <= resp.status_code < 300:
            return
        if resp.status_code in {401, 403}:
            raise ZWorkforceBridgeError(
                f"zWorkforce {operation} authentication was rejected",
                status_code=503,
            )
        raise ZWorkforceBridgeError(
            f"zWorkforce {operation} failed with upstream status {resp.status_code}",
            status_code=502,
        )

    @classmethod
    async def get_overview(cls) -> Dict[str, Any]:
        base_url = cls._base_url()
        try:
            async with httpx.AsyncClient(timeout=cls.OVERVIEW_TIMEOUT_SECONDS) as client:
                resp = await client.get(
                    f"{base_url}/api/v1/overview",
                    headers=cls._headers(),
                )
        except httpx.RequestError as exc:
            raise ZWorkforceBridgeError("zWorkforce control plane is unavailable") from exc
        cls._raise_for_status(resp, "overview")
        return cls._decode_json(resp, "overview")

    @classmethod
    async def dispatch_task(
        cls,
        title: str,
        prompt: str,
        target_agent: str = "general",
    ) -> Dict[str, Any]:
        base_url = cls._base_url()
        payload = {
            "title": title,
            "prompt": prompt,
            "agent": target_agent,
            "source": "zider_sidebar",
        }
        try:
            async with httpx.AsyncClient(timeout=cls.DISPATCH_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    f"{base_url}/api/v1/tasks",
                    json=payload,
                    headers=cls._headers(),
                )
        except httpx.RequestError as exc:
            raise ZWorkforceBridgeError("zWorkforce control plane is unavailable") from exc
        cls._raise_for_status(resp, "task dispatch")
        return cls._decode_json(resp, "task dispatch")
