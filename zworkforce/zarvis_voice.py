from __future__ import annotations

from dataclasses import dataclass
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


@dataclass(frozen=True)
class ZarvisVoiceConfig:
    enabled: bool
    gateway_url: str
    service_token: str
    websocket_allowlist: tuple[str, ...]
    model: str
    timeout_seconds: float


class ZarvisVoiceError(RuntimeError):
    def __init__(self, message: str, *, status: int = 502, code: str = "voice_unavailable") -> None:
        super().__init__(message)
        self.status = status
        self.code = code


def _bool_env(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _origin(value: str, *, schemes: set[str]) -> str:
    parsed = urllib.parse.urlsplit(value.strip())
    if parsed.scheme not in schemes or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f"invalid URL: {value!r}")
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname}{port}"


def _gateway_url(value: str) -> str:
    if not value:
        return ""
    parsed = urllib.parse.urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("ZWORKFORCE_ZARVIS_VOICE_GATEWAY_URL must be an http(s) URL without credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("ZWORKFORCE_ZARVIS_VOICE_GATEWAY_URL must not contain query or fragment components")
    return value.strip().rstrip("/")


def load_voice_config() -> ZarvisVoiceConfig:
    gateway = _gateway_url(
        os.getenv("ZWORKFORCE_ZARVIS_VOICE_GATEWAY_URL", "").strip()
        or os.getenv("Z_PLATFORM_VOICE_GATEWAY_URL", "").strip()
    )
    token = (
        os.getenv("ZWORKFORCE_ZARVIS_VOICE_SERVICE_TOKEN", "").strip()
        or os.getenv("Z_PLATFORM_SERVICE_TOKEN", "").strip()
    )
    raw_allowlist = os.getenv("ZWORKFORCE_ZARVIS_VOICE_WS_ALLOWLIST", "").strip()
    allowlist: list[str] = []
    for raw in raw_allowlist.split(",") if raw_allowlist else ():
        value = _origin(raw, schemes={"ws", "wss"})
        if value not in allowlist:
            allowlist.append(value)
    timeout = float(os.getenv("ZWORKFORCE_ZARVIS_VOICE_TIMEOUT_SECONDS", "5"))
    if not 0.25 <= timeout <= 30:
        raise ValueError("ZWORKFORCE_ZARVIS_VOICE_TIMEOUT_SECONDS must be between 0.25 and 30")
    model = os.getenv("ZWORKFORCE_ZARVIS_VOICE_MODEL", "default").strip() or "default"
    if len(model) > 256:
        raise ValueError("ZWORKFORCE_ZARVIS_VOICE_MODEL must be <= 256 characters")
    return ZarvisVoiceConfig(
        enabled=_bool_env("ZWORKFORCE_ZARVIS_VOICE_ENABLED"),
        gateway_url=gateway,
        service_token=token,
        websocket_allowlist=tuple(allowlist),
        model=model,
        timeout_seconds=timeout,
    )


class ZarvisVoiceService:
    def __init__(self, config: ZarvisVoiceConfig | None = None, *, opener: Any = None) -> None:
        self.config = config or load_voice_config()
        self._opener = opener or urllib.request.urlopen
        if self.config.enabled and not self.config.gateway_url:
            raise ValueError("Z.A.R.V.I.S. voice is enabled but the voice gateway URL is missing")
        if self.config.enabled and not self.config.service_token:
            raise ValueError("Z.A.R.V.I.S. voice is enabled but the voice service token is missing")
        if self.config.enabled and os.getenv("ZWORKFORCE_ENV", "development").strip().lower() == "production" and not self.config.websocket_allowlist:
            raise ValueError("ZWORKFORCE_ZARVIS_VOICE_WS_ALLOWLIST is required in production when voice is enabled")

    @property
    def csp_connect_sources(self) -> tuple[str, ...]:
        return self.config.websocket_allowlist if self.config.enabled else ()

    @property
    def microphone_enabled(self) -> bool:
        return self.config.enabled

    def snapshot(self) -> dict[str, Any]:
        return {
            "enabled": self.config.enabled,
            "configured": bool(self.config.gateway_url and self.config.service_token),
            "model": self.config.model if self.config.enabled else None,
            "websocket_origins": list(self.config.websocket_allowlist),
            "transport": "realtime-pcm16" if self.config.enabled else None,
        }

    def issue_session(self, *, tenant_id: str, subject_id: str, request_id: str, model: str | None = None) -> dict[str, Any]:
        if not self.config.enabled:
            raise ZarvisVoiceError("Z.A.R.V.I.S. voice is disabled", status=503, code="voice_disabled")
        if not self.config.gateway_url or not self.config.service_token:
            raise ZarvisVoiceError("Z.A.R.V.I.S. voice is not configured", status=503, code="voice_not_configured")

        selected_model = (model or self.config.model).strip()
        if not selected_model or len(selected_model) > 256:
            raise ZarvisVoiceError("invalid voice model", status=400, code="invalid_voice_model")
        body = json.dumps({"model": selected_model}, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.gateway_url}/v1/voice/tickets",
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.service_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Tenant-Id": tenant_id,
                "X-Subject-Id": subject_id,
                "X-Request-Id": request_id,
            },
            method="POST",
        )
        try:
            with self._opener(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read(64 * 1024 + 1)
                if len(raw) > 64 * 1024:
                    raise ZarvisVoiceError("voice gateway response is too large", code="voice_gateway_invalid_response")
        except urllib.error.HTTPError as exc:
            status = 503 if exc.code in {429, 503} else 502
            raise ZarvisVoiceError("voice gateway rejected the session request", status=status, code="voice_gateway_rejected") from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
            raise ZarvisVoiceError("voice gateway is unavailable", status=503, code="voice_gateway_unavailable") from exc

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ZarvisVoiceError("voice gateway returned invalid JSON", code="voice_gateway_invalid_response") from exc
        if not isinstance(payload, dict):
            raise ZarvisVoiceError("voice gateway returned an invalid response", code="voice_gateway_invalid_response")

        ticket = payload.get("ticket")
        expires_at = payload.get("expires_at")
        websocket_url = payload.get("websocket_url")
        if not isinstance(ticket, str) or not ticket or len(ticket) > 4096:
            raise ZarvisVoiceError("voice gateway returned an invalid ticket", code="voice_gateway_invalid_response")
        if not isinstance(expires_at, str) or not expires_at or len(expires_at) > 128:
            raise ZarvisVoiceError("voice gateway returned an invalid expiry", code="voice_gateway_invalid_response")
        if not isinstance(websocket_url, str) or len(websocket_url) > 2048:
            raise ZarvisVoiceError("voice gateway returned an invalid WebSocket URL", code="voice_gateway_invalid_response")

        try:
            websocket_origin = _origin(websocket_url, schemes={"ws", "wss"})
        except ValueError as exc:
            raise ZarvisVoiceError("voice gateway returned an invalid WebSocket URL", code="voice_gateway_invalid_response") from exc
        if self.config.websocket_allowlist and websocket_origin not in self.config.websocket_allowlist:
            raise ZarvisVoiceError("voice gateway WebSocket origin is not allowlisted", status=502, code="voice_websocket_origin_denied")

        return {
            "ticket": ticket,
            "expires_at": expires_at,
            "websocket_url": websocket_url,
            "ticket_transport": "sec-websocket-protocol",
            "model": selected_model,
            "transport": "realtime-pcm16",
        }


def build_zarvis_voice_service() -> ZarvisVoiceService:
    return ZarvisVoiceService()
