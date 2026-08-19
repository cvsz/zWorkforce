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
            raise ValueError("ZWORKFORCE_ZKNOWBASE_URL and ZWORKFORCE_ZKNOWBASE_API_KEY must be configured together")
        timeout = max(1.0, float(os.getenv("ZWORKFORCE_ZKNOWBASE_TIMEOUT_SECONDS", "30")))
        return cls(base_url=base_url, api_key=api_key, timeout_seconds=timeout)


class ZKnowbaseClient:
    def __init__(self, config: ZKnowbaseConfig):
        self.config = config

    def ask(self, question: str, *, top_k: int = 5) -> dict[str, Any]:
        return self._post("/api/v1/query", {"question": question, "top_k": top_k, "stream": False})

    def search(self, query: str, *, top_k: int = 5) -> dict[str, Any]:
        return self._post("/api/v1/search", {"query": query, "top_k": top_k})

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/health")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, payload)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {"Accept": "application/json", "X-API-Key": self.config.api_key}
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = request.Request(f"{self.config.base_url}{path}", data=body, headers=headers, method=method)
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
