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
                "ZWORKFORCE_ZKNOWBASE_URL and ZWORKFORCE_ZKNOWBASE_API_KEY "
                "must be configured together"
            )
        timeout = max(
            1.0,
            float(os.getenv("ZWORKFORCE_ZKNOWBASE_TIMEOUT_SECONDS", "30")),
        )
        return cls(base_url=base_url, api_key=api_key, timeout_seconds=timeout)


@dataclass(frozen=True)
class ZKnowbaseExecutionContext:
    """Governed execution identity propagated to zknowbase retrieval calls."""

    tenant_id: str
    actor_id: str
    agent_id: str
    tool_id: str
    policy_context: str
    request_id: str
    trace_id: str

    def headers(self) -> dict[str, str]:
        values = {
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "agent_id": self.agent_id,
            "tool_id": self.tool_id,
            "policy_context": self.policy_context,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
        }
        normalized: dict[str, str] = {}
        for name, value in values.items():
            bounded = value.strip()
            if not bounded or len(bounded) > 256 or any(ord(char) < 32 for char in bounded):
                raise ValueError(f"invalid zknowbase execution context field: {name}")
            normalized[name] = bounded
        return {
            "X-Request-ID": normalized["request_id"],
            "X-ZWorkforce-Context-Version": "1",
            "X-ZWorkforce-Tenant-ID": normalized["tenant_id"],
            "X-ZWorkforce-Actor-ID": normalized["actor_id"],
            "X-ZWorkforce-Agent-ID": normalized["agent_id"],
            "X-ZWorkforce-Tool-ID": normalized["tool_id"],
            "X-ZWorkforce-Policy-Context": normalized["policy_context"],
            "X-ZWorkforce-Request-ID": normalized["request_id"],
            "X-ZWorkforce-Trace-ID": normalized["trace_id"],
        }


class ZKnowbaseClient:
    def __init__(self, config: ZKnowbaseConfig):
        self.config = config

    def ask(
        self,
        question: str,
        *,
        context: ZKnowbaseExecutionContext,
        top_k: int = 5,
    ) -> dict[str, Any]:
        return self._post(
            "/api/v1/query",
            {"question": question, "top_k": top_k, "stream": False},
            context=context,
        )

    def search(
        self,
        query: str,
        *,
        context: ZKnowbaseExecutionContext,
        top_k: int = 5,
    ) -> dict[str, Any]:
        return self._post(
            "/api/v1/search",
            {"query": query, "top_k": top_k},
            context=context,
        )

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/health")

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        context: ZKnowbaseExecutionContext,
    ) -> dict[str, Any]:
        return self._request("POST", path, payload, context=context)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        context: ZKnowbaseExecutionContext | None = None,
    ) -> dict[str, Any]:
        body = (
            None
            if payload is None
            else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        headers = {"Accept": "application/json", "X-API-Key": self.config.api_key}
        if context is not None:
            headers.update(context.headers())
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = request.Request(
            f"{self.config.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
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
