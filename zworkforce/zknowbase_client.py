from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any
from urllib import error, request


class ZKnowbaseError(RuntimeError):
    pass


_TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")


def _tenant(value: str) -> str:
    normalized = value.strip().lower()
    if not _TENANT_RE.fullmatch(normalized):
        raise ValueError(f"invalid zknowbase tenant id: {value!r}")
    return normalized


def _header(value: str, limit: int = 160) -> str:
    return " ".join(str(value).split())[:limit]


@dataclass(frozen=True)
class ZKnowbaseRequestContext:
    tenant_id: str
    actor: str
    agent_id: str
    tool: str
    request_id: str
    policy_context: str = "agent_tool_grant"


@dataclass(frozen=True)
class ZKnowbaseConfig:
    base_url: str
    api_key: str = ""
    timeout_seconds: float = 30.0
    tenant_id: str = "default"
    tenant_api_keys: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "ZKnowbaseConfig | None":
        base_url = os.getenv("ZWORKFORCE_ZKNOWBASE_URL", "").strip().rstrip("/")
        api_key = os.getenv("ZWORKFORCE_ZKNOWBASE_API_KEY", "").strip()
        keys_raw = os.getenv("ZWORKFORCE_ZKNOWBASE_TENANT_KEYS_JSON", "").strip()
        if not base_url and not api_key and not keys_raw:
            return None
        if not base_url:
            raise ValueError("ZWORKFORCE_ZKNOWBASE_URL is required when zknowbase integration is configured")
        if api_key and keys_raw:
            raise ValueError(
                "configure either ZWORKFORCE_ZKNOWBASE_API_KEY or "
                "ZWORKFORCE_ZKNOWBASE_TENANT_KEYS_JSON, not both"
            )

        tenant_keys: dict[str, str] = {}
        if keys_raw:
            try:
                parsed = json.loads(keys_raw)
            except json.JSONDecodeError as exc:
                raise ValueError("ZWORKFORCE_ZKNOWBASE_TENANT_KEYS_JSON must be valid JSON") from exc
            if not isinstance(parsed, dict) or not parsed:
                raise ValueError("ZWORKFORCE_ZKNOWBASE_TENANT_KEYS_JSON must be a non-empty object")
            for raw_tenant, raw_key in parsed.items():
                tenant_id = _tenant(str(raw_tenant))
                key = str(raw_key).strip()
                if not key:
                    raise ValueError(f"zknowbase API key is empty for tenant {tenant_id}")
                tenant_keys[tenant_id] = key
        elif not api_key:
            raise ValueError(
                "ZWORKFORCE_ZKNOWBASE_API_KEY or ZWORKFORCE_ZKNOWBASE_TENANT_KEYS_JSON is required"
            )

        timeout = max(1.0, min(float(os.getenv("ZWORKFORCE_ZKNOWBASE_TIMEOUT_SECONDS", "30")), 120.0))
        bound_tenant = _tenant(
            os.getenv(
                "ZWORKFORCE_ZKNOWBASE_TENANT_ID",
                os.getenv("ZWORKFORCE_DEFAULT_TENANT", "default"),
            )
        )
        return cls(
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout,
            tenant_id=bound_tenant,
            tenant_api_keys=tenant_keys,
        )

    def key_for_tenant(self, tenant_id: str) -> str:
        tenant_id = _tenant(tenant_id)
        if self.tenant_api_keys:
            key = self.tenant_api_keys.get(tenant_id)
            if not key:
                raise ZKnowbaseError(f"no zknowbase service credential is configured for tenant {tenant_id}")
            return key
        if tenant_id != self.tenant_id:
            raise ZKnowbaseError(
                f"zknowbase credential is bound to tenant {self.tenant_id}, not {tenant_id}"
            )
        if not self.api_key:
            raise ZKnowbaseError("zknowbase service credential is unavailable")
        return self.api_key


class ZKnowbaseClient:
    def __init__(self, config: ZKnowbaseConfig):
        self.config = config

    def ask(self, question: str, *, top_k: int = 5) -> dict[str, Any]:
        return self._post(
            "/api/v1/query",
            {"question": question, "top_k": self._top_k(top_k), "stream": False},
            api_key=self.config.api_key,
        )

    def search(self, query: str, *, top_k: int = 5) -> dict[str, Any]:
        return self._post(
            "/api/v1/search",
            {"query": query, "top_k": self._top_k(top_k)},
            api_key=self.config.api_key,
        )

    def ask_for_tenant(
        self,
        context: ZKnowbaseRequestContext,
        question: str,
        *,
        top_k: int = 5,
    ) -> dict[str, Any]:
        payload = self._post(
            "/api/v1/query",
            {"question": question, "top_k": self._top_k(top_k), "stream": False},
            api_key=self.config.key_for_tenant(context.tenant_id),
            context=context,
        )
        self._validate_tenant_payload(payload, context.tenant_id, "sources")
        return payload

    def search_for_tenant(
        self,
        context: ZKnowbaseRequestContext,
        query: str,
        *,
        top_k: int = 5,
    ) -> dict[str, Any]:
        payload = self._post(
            "/api/v1/search",
            {"query": query, "top_k": self._top_k(top_k)},
            api_key=self.config.key_for_tenant(context.tenant_id),
            context=context,
        )
        self._validate_tenant_payload(payload, context.tenant_id, "results")
        return payload

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/health", api_key=self.config.api_key)

    @staticmethod
    def _top_k(value: int) -> int:
        value = int(value)
        if value < 1 or value > 20:
            raise ZKnowbaseError("zknowbase top_k must be between 1 and 20")
        return value

    @staticmethod
    def _validate_tenant_payload(payload: dict[str, Any], tenant_id: str, key: str) -> None:
        items = payload.get(key)
        if not isinstance(items, list):
            raise ZKnowbaseError(f"zknowbase response is missing {key}")
        for item in items:
            if not isinstance(item, dict):
                raise ZKnowbaseError("zknowbase returned an invalid citation/result")
            response_tenant = item.get("tenant_id")
            if not isinstance(response_tenant, str) or response_tenant != tenant_id:
                raise ZKnowbaseError("zknowbase returned data outside the requested tenant boundary")

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        api_key: str,
        context: ZKnowbaseRequestContext | None = None,
    ) -> dict[str, Any]:
        return self._request("POST", path, payload, api_key=api_key, context=context)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        api_key: str,
        context: ZKnowbaseRequestContext | None = None,
    ) -> dict[str, Any]:
        if not api_key:
            raise ZKnowbaseError("zknowbase service credential is unavailable")
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {"Accept": "application/json", "X-API-Key": api_key}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if context is not None:
            headers.update(
                {
                    "X-Request-ID": _header(context.request_id, 128),
                    "X-ZWorkforce-Actor": _header(context.actor),
                    "X-ZWorkforce-Agent": _header(context.agent_id),
                    "X-ZWorkforce-Tool": _header(context.tool, 64),
                    "X-ZWorkforce-Policy-Context": _header(context.policy_context),
                }
            )
        req = request.Request(
            f"{self.config.base_url}{path}", data=body, headers=headers, method=method
        )
        try:
            with request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                raw = response.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ZKnowbaseError(f"zknowbase HTTP {exc.code}: {detail[:512]}") from exc
        except error.URLError as exc:
            raise ZKnowbaseError(f"zknowbase unavailable: {exc.reason}") from exc
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ZKnowbaseError("zknowbase returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise ZKnowbaseError("zknowbase returned a non-object JSON response")
        return parsed
