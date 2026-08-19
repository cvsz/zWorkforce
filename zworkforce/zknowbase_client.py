from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, request


class ZKnowbaseError(RuntimeError):
    pass


@dataclass(frozen=True)
class ZKnowbaseConfig:
    base_url: str
    api_key: str
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "ZKnowbaseConfig | None":
        base_url = os.getenv("ZWORKFORCE_ZKNOWBASE_URL", "").strip().rstrip("/")
        api_key = os.getenv("ZWORKFORCE_ZKNOWBASE_API_KEY", "").strip()
        if not base_url and not api_key:
            return None
        if not base_url or not api_key:
            raise ValueError(
                "ZWORKFORCE_ZKNOWBASE_URL and ZWORKFORCE_ZKNOWBASE_API_KEY must be configured together"
            )
        timeout = _bounded_timeout(os.getenv("ZWORKFORCE_ZKNOWBASE_TIMEOUT_SECONDS", "30"))
        return cls(base_url=base_url, api_key=api_key, timeout_seconds=timeout)


class ZKnowbaseRegistry:
    """Resolve a server-side zknowbase credential for the authoritative task tenant.

    Governed retrieval must never use a global credential without an explicit tenant
    binding. Multi-tenant deployments may provide a bounded JSON map; single-tenant
    deployments can keep the original URL/key variables and add an explicit tenant ID.
    """

    MAX_CONFIG_BYTES = 64 * 1024
    MAX_TENANTS = 256

    def __init__(self, configs: dict[str, ZKnowbaseConfig]):
        self._configs = dict(configs)

    @classmethod
    def from_env(cls) -> "ZKnowbaseRegistry":
        raw = os.getenv("ZWORKFORCE_ZKNOWBASE_TENANTS_JSON", "").strip()
        legacy_url = os.getenv("ZWORKFORCE_ZKNOWBASE_URL", "").strip()
        legacy_key = os.getenv("ZWORKFORCE_ZKNOWBASE_API_KEY", "").strip()
        legacy_tenant = os.getenv("ZWORKFORCE_ZKNOWBASE_TENANT_ID", "").strip()

        if raw:
            if legacy_url or legacy_key or legacy_tenant:
                raise ValueError(
                    "ZWORKFORCE_ZKNOWBASE_TENANTS_JSON cannot be combined with single-tenant zknowbase settings"
                )
            if len(raw.encode("utf-8")) > cls.MAX_CONFIG_BYTES:
                raise ValueError("ZWORKFORCE_ZKNOWBASE_TENANTS_JSON exceeds size limit")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("ZWORKFORCE_ZKNOWBASE_TENANTS_JSON must be valid JSON") from exc
            if not isinstance(parsed, dict) or len(parsed) > cls.MAX_TENANTS:
                raise ValueError("ZWORKFORCE_ZKNOWBASE_TENANTS_JSON must be a bounded object")
            configs: dict[str, ZKnowbaseConfig] = {}
            for tenant_id, item in parsed.items():
                tenant = str(tenant_id).strip()
                if not tenant or not isinstance(item, dict):
                    raise ValueError("Each zknowbase tenant entry must be an object")
                base_url = str(item.get("url", "")).strip().rstrip("/")
                api_key = str(item.get("api_key", "")).strip()
                if not base_url or not api_key:
                    raise ValueError(f"zknowbase tenant {tenant!r} requires url and api_key")
                timeout = _bounded_timeout(item.get("timeout_seconds", 30))
                configs[tenant] = ZKnowbaseConfig(base_url, api_key, timeout)
            return cls(configs)

        config = ZKnowbaseConfig.from_env()
        if config is None:
            return cls({})
        if not legacy_tenant:
            raise ValueError(
                "ZWORKFORCE_ZKNOWBASE_TENANT_ID is required for governed retrieval with a single zknowbase credential"
            )
        return cls({legacy_tenant: config})

    def resolve(self, tenant_id: str) -> ZKnowbaseConfig:
        tenant = str(tenant_id).strip()
        if not tenant:
            raise ZKnowbaseError("tenant context is required for zknowbase retrieval")
        config = self._configs.get(tenant)
        if config is None:
            raise ZKnowbaseError(f"zknowbase is not configured for tenant {tenant!r}")
        return config


def _bounded_timeout(value: object) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("zknowbase timeout must be numeric") from exc
    if not 1.0 <= timeout <= 120.0:
        raise ValueError("zknowbase timeout must be between 1 and 120 seconds")
    return timeout


class ZKnowbaseClient:
    def __init__(self, config: ZKnowbaseConfig):
        self.config = config

    def ask(self, question: str, *, top_k: int = 5, request_id: str | None = None) -> dict[str, Any]:
        return self._post(
            "/api/v1/query",
            {"question": question, "top_k": _bounded_top_k(top_k), "stream": False},
            request_id=request_id,
        )

    def search(self, query: str, *, top_k: int = 5, request_id: str | None = None) -> dict[str, Any]:
        return self._post(
            "/api/v1/search",
            {"query": query, "top_k": _bounded_top_k(top_k)},
            request_id=request_id,
        )

    def health(self, *, request_id: str | None = None) -> dict[str, Any]:
        return self._request("GET", "/api/v1/health", request_id=request_id)

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return self._request("POST", path, payload, request_id=request_id)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {"Accept": "application/json", "X-API-Key": self.config.api_key}
        if request_id:
            headers["X-Request-ID"] = str(request_id)[:128]
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = request.Request(
            f"{self.config.base_url}{path}", data=body, headers=headers, method=method
        )
        try:
            with request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
        except error.HTTPError as exc:
            detail = exc.read(513).decode("utf-8", errors="replace")
            raise ZKnowbaseError(f"zknowbase HTTP {exc.code}: {detail[:512]}") from exc
        except error.URLError as exc:
            raise ZKnowbaseError(f"zknowbase unavailable: {exc.reason}") from exc
        if len(raw) > 2 * 1024 * 1024:
            raise ZKnowbaseError("zknowbase response exceeds size limit")
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ZKnowbaseError("zknowbase returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise ZKnowbaseError("zknowbase returned a non-object JSON response")
        return parsed


def _bounded_top_k(value: int) -> int:
    top_k = int(value)
    if not 1 <= top_k <= 50:
        raise ValueError("zknowbase top_k must be between 1 and 50")
    return top_k
