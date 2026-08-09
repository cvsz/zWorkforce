from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import time
import urllib.parse
import urllib.request
import uuid


class OtlpHttpExporter:
    def __init__(self, endpoint: str, headers: dict[str, str] | None = None, timeout: float = 5.0):
        self.endpoint = str(endpoint or "").strip()
        self.headers = dict(headers or {})
        self.timeout = max(1.0, float(timeout))
        if self.endpoint:
            p = urllib.parse.urlsplit(self.endpoint)
            if p.scheme not in {"http", "https"} or not p.hostname:
                raise ValueError("invalid OTLP traces endpoint")
            if p.scheme != "https" and p.hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("remote OTLP traces endpoint must use HTTPS")

    def export(self, name: str, started_ns: int, ended_ns: int, attributes: dict | None = None, status: str = "OK") -> None:
        if not self.endpoint:
            return
        trace_id = uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]
        body = {
            "resourceSpans": [{
                "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "zworkforce"}}]},
                "scopeSpans": [{"scope": {"name": "zworkforce"}, "spans": [{
                    "traceId": trace_id, "spanId": span_id, "name": name,
                    "kind": 1, "startTimeUnixNano": str(started_ns), "endTimeUnixNano": str(ended_ns),
                    "attributes": [{"key": str(k), "value": {"stringValue": str(v)}} for k, v in (attributes or {}).items()],
                    "status": {"code": 1 if status == "OK" else 2},
                }]}],
            }]
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json", **self.headers}
        req = urllib.request.Request(self.endpoint, data=json.dumps(body, separators=(",", ":")).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp.read(1024)
        except Exception:
            # Telemetry must never make task execution fail.
            return


class _TelemetryProvider:
    def __init__(self, provider, exporter: OtlpHttpExporter):
        self._provider = provider
        self._exporter = exporter

    def __getattr__(self, name):
        return getattr(self._provider, name)

    def chat(self, tier, messages, tools):
        start = time.time_ns()
        status = "OK"
        try:
            result = self._provider.chat(tier, messages, tools)
            return result
        except Exception:
            status = "ERROR"
            raise
        finally:
            self._exporter.export("provider.chat", start, time.time_ns(), {"tier": tier}, status)


def wrap_provider_from_env(provider):
    endpoint = os.getenv("ZWORKFORCE_OTLP_TRACES_ENDPOINT", "").strip()
    if not endpoint:
        return provider
    headers: dict[str, str] = {}
    raw = os.getenv("ZWORKFORCE_OTLP_HEADERS_JSON", "").strip()
    if raw:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("ZWORKFORCE_OTLP_HEADERS_JSON must be an object")
        headers = {str(k): str(v) for k, v in parsed.items()}
    return _TelemetryProvider(provider, OtlpHttpExporter(endpoint, headers))
