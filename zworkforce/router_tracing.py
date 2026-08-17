from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from typing import Any


@dataclass
class RouterTelemetrySpan:
    model: str
    tenant_id: str
    prompt_tokens: int
    completion_tokens: int
    total_cost_usd: float
    latency_ms: float
    timestamp: float = field(default_factory=time.time)


class RouterTelemetryCollector:
    """Collects and broadcasts OpenRouter model usage, latency, and cost attribution telemetry."""
    # Approximate pricing per 1M tokens (zero for free tier)
    MODEL_RATES = {
        "deepseek/deepseek-r1:free": 0.0,
        "meta-llama/llama-3.3-70b-instruct:free": 0.0,
        "google/gemini-2.0-flash-exp:free": 0.0,
        "anthropic/claude-3.5-sonnet": 3.00,
        "openai/gpt-4o": 2.50,
    }

    def __init__(self):
        self._spans: list[RouterTelemetrySpan] = []

    def record_usage(
        self,
        tenant_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
    ) -> RouterTelemetrySpan:
        rate = self.MODEL_RATES.get(model, 1.0)
        total_tokens = prompt_tokens + completion_tokens
        cost = (total_tokens / 1_000_000) * rate

        span = RouterTelemetrySpan(
            model=model,
            tenant_id=tenant_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_cost_usd=round(cost, 6),
            latency_ms=latency_ms,
        )
        self._spans.append(span)
        return span

    def get_tenant_summary(self, tenant_id: str) -> dict[str, Any]:
        tenant_spans = [s for s in self._spans if s.tenant_id == tenant_id]
        total_cost = sum(s.total_cost_usd for s in tenant_spans)
        total_tokens = sum(s.prompt_tokens + s.completion_tokens for s in tenant_spans)
        avg_latency = (
            sum(s.latency_ms for s in tenant_spans) / len(tenant_spans)
            if tenant_spans
            else 0.0
        )
        return {
            "tenant_id": tenant_id,
            "total_requests": len(tenant_spans),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "average_latency_ms": round(avg_latency, 2),
        }
