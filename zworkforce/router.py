from __future__ import annotations

import re

TIERS = ("luna", "terra", "sol")


class ModelRouter:
    HARD_TERMS = re.compile(
        r"\b(architecture|security|threat model|race condition|deadlock|distributed|migration|root cause|"
        r"refactor|cryptograph|formal proof|production incident|debug|incident response|compliance|financial model)\b",
        re.I,
    )
    LIGHT_TERMS = re.compile(r"\b(summarize|format|classify|extract|tag|rename|translate|normalize|rewrite|deduplicate)\b", re.I)

    def choose(
        self,
        prompt: str,
        default_tier: str = "terra",
        mutating: bool = False,
        override: str | None = None,
        context_bytes: int = 0,
        tool_count: int = 0,
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
        return tier, {"reason": "complexity_router", "score": score, "estimated_context": length}

    @staticmethod
    def escalate(tier: str) -> str | None:
        try:
            idx = TIERS.index(tier)
        except ValueError:
            return None
        return TIERS[idx + 1] if idx + 1 < len(TIERS) else None
