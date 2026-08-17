from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

TIERS = ("luna", "terra", "sol")

# Recognized free tier models with their capability profiles
FREE_MODEL_SPECS: dict[str, dict[str, Any]] = {
    "openrouter/free": {
        "provider": "openrouter",
        "toolcall": True,
        "reasoning": True,
        "input_image": True,
        "input_pdf": True,
        "context_window": 128_000,
        "is_free": True,
    },
    "meta-llama/llama-3.3-70b-instruct:free": {
        "provider": "openrouter",
        "toolcall": True,
        "reasoning": False,
        "input_image": False,
        "input_pdf": False,
        "context_window": 131_072,
        "is_free": True,
    },
    "deepseek/deepseek-r1:free": {
        "provider": "openrouter",
        "toolcall": True,
        "reasoning": True,
        "input_image": False,
        "input_pdf": False,
        "context_window": 64_000,
        "is_free": True,
    },
    "qwen/qwen-2.5-coder-32b-instruct:free": {
        "provider": "openrouter",
        "toolcall": True,
        "reasoning": False,
        "input_image": False,
        "input_pdf": False,
        "context_window": 32_768,
        "is_free": True,
    },
    "google/gemini-2.0-flash-lite:free": {
        "provider": "openrouter",
        "toolcall": True,
        "reasoning": False,
        "input_image": True,
        "input_pdf": True,
        "context_window": 1_048_576,
        "is_free": True,
    },
    "llama-3.3-70b-versatile": {
        "provider": "groq",
        "toolcall": True,
        "reasoning": False,
        "input_image": False,
        "input_pdf": False,
        "context_window": 128_000,
        "is_free": True,
    },
    "deepseek-r1-distill-llama-70b": {
        "provider": "groq",
        "toolcall": True,
        "reasoning": True,
        "input_image": False,
        "input_pdf": False,
        "context_window": 128_000,
        "is_free": True,
    },
}


@dataclass(frozen=True)
class ModelCapabilities:
    toolcall: bool = True
    reasoning: bool = False
    temperature: bool = True
    input_image: bool = False
    input_pdf: bool = False
    input_audio: bool = False
    output_audio: bool = False
    interleaved_reasoning: bool = False
    context_window: int = 128_000
    is_free: bool = False


@dataclass(frozen=True)
class ModelMetadata:
    id: str
    provider: str
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    input_cost_per_m: float = 0.0
    output_cost_per_m: float = 0.0
    cache_read_cost_per_m: float = 0.0
    cache_write_cost_per_m: float = 0.0
    status: str = "active"


class ModelRouter:
    HARD_TERMS = re.compile(
        r"\b(architecture|security|threat model|race condition|deadlock|distributed|migration|root cause|"
        r"refactor|cryptograph|formal proof|production incident|debug|incident response|compliance|financial model)\b",
        re.I,
    )
    LIGHT_TERMS = re.compile(r"\b(summarize|format|classify|extract|tag|rename|translate|normalize|rewrite|deduplicate)\b", re.I)

    def __init__(self, catalog: dict[str, ModelMetadata] | None = None):
        self.catalog = catalog or self._build_default_catalog()

    @staticmethod
    def _build_default_catalog() -> dict[str, ModelMetadata]:
        out = {}
        for mid, spec in FREE_MODEL_SPECS.items():
            caps = ModelCapabilities(
                toolcall=spec.get("toolcall", True),
                reasoning=spec.get("reasoning", False),
                input_image=spec.get("input_image", False),
                input_pdf=spec.get("input_pdf", False),
                context_window=spec.get("context_window", 128_000),
                is_free=spec.get("is_free", True),
            )
            out[mid] = ModelMetadata(id=mid, provider=spec["provider"], capabilities=caps)
        return out

    @staticmethod
    def parse_variant_slug(model_id: str) -> tuple[str, str | None]:
        """Extract base model ID and optional variant slug like :free, :thinking, :exacto, :nitro, :online, :extended."""
        if not model_id:
            return "", None
        clean = model_id.strip()
        for variant in (":thinking", ":exacto", ":nitro", ":online", ":extended", ":free"):
            if clean.endswith(variant):
                return clean[:-len(variant)], variant[1:]
        return clean, None

    def resolve_smart_variant(self, model_id: str, *, variant: str | None = None) -> str:
        """Resolve model ID combined with smart variant slug for optimized routing."""
        base, explicit_variant = self.parse_variant_slug(model_id)
        effective_variant = (variant or explicit_variant or "").lower()
        if not effective_variant:
            return base

        if effective_variant == "free":
            candidate = f"{base}:free" if not base.endswith(":free") else base
            if candidate in self.catalog and self.catalog[candidate].capabilities.is_free:
                return candidate
            if base in self.catalog and self.catalog[base].capabilities.is_free:
                return base
            resolved = self.resolve_free_model()
            return resolved or "openrouter/free"
        elif effective_variant == "thinking":
            return f"{base}:thinking" if not base.endswith(":thinking") else base
        elif effective_variant == "nitro":
            return f"{base}:nitro" if not base.endswith(":nitro") else base
        elif effective_variant == "exacto":
            return f"{base}:exacto" if not base.endswith(":exacto") else base
        elif effective_variant == "online":
            return f"{base}:online" if not base.endswith(":online") else base
        elif effective_variant == "extended":
            return f"{base}:extended" if not base.endswith(":extended") else base
        return f"{base}:{effective_variant}"

    def resolve_free_model(
        self,
        required_tools: bool = False,
        required_vision: bool = False,
        required_pdf: bool = False,
        required_reasoning: bool = False,
    ) -> str | None:
        """Find the best zero-cost model matching required capabilities."""
        for mid, meta in self.catalog.items():
            caps = meta.capabilities
            if not caps.is_free:
                continue
            if required_tools and not caps.toolcall:
                continue
            if required_vision and not caps.input_image:
                continue
            if required_pdf and not caps.input_pdf:
                continue
            if required_reasoning and not caps.reasoning:
                continue
            return mid
        return "openrouter/free"

    def choose(
        self,
        prompt: str,
        default_tier: str = "terra",
        mutating: bool = False,
        override: str | None = None,
        context_bytes: int = 0,
        tool_count: int = 0,
        prefer_free: bool = True,
    ) -> tuple[str, dict]:
        if override:
            if override not in TIERS:
                raise ValueError("tier_override must be luna, terra, or sol")
            return override, {"reason": "explicit_override", "score": 0}
        text = prompt.strip()
        score = 3
        length = len(text) + max(0, context_bytes // 4)
        if length > 16_000:
            score += 3
        elif length > 4_000:
            score += 2
        elif length > 1_200:
            score += 1
        if self.HARD_TERMS.search(text):
            score += 2
        if self.LIGHT_TERMS.search(text):
            score -= 2
        if mutating:
            score += 1
        if tool_count >= 5:
            score += 1
        if any(x in text for x in ("```", "Traceback", "Exception", "stack trace", "segmentation fault")):
            score += 1
        if default_tier == "sol":
            score += 1
        elif default_tier == "luna":
            score -= 1
        tier = "luna" if score <= 2 else "terra" if score <= 5 else "sol"

        free_candidate = None
        if prefer_free:
            free_candidate = self.resolve_free_model(
                required_tools=(tool_count > 0 or mutating),
                required_reasoning=(score >= 6),
            )

        rationale = {
            "reason": "complexity_router",
            "score": score,
            "estimated_context": length,
            "free_candidate": free_candidate,
            "free_first": prefer_free,
        }
        return tier, rationale

    @staticmethod
    def escalate(tier: str) -> str | None:
        try:
            idx = TIERS.index(tier)
        except ValueError:
            return None
        return TIERS[idx + 1] if idx + 1 < len(TIERS) else None
