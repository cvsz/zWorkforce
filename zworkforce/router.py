from __future__ import annotations
import re
TIERS = ("luna", "terra", "sol")
class ModelRouter:
    HARD_TERMS = re.compile(r"\b(architecture|security|threat model|race condition|deadlock|distributed|migration|root cause|refactor|cryptograph|formal proof|production incident|debug)\b", re.I)
    LIGHT_TERMS = re.compile(r"\b(summarize|format|classify|extract|tag|rename|translate|normalize|rewrite)\b", re.I)
    def choose(self, prompt: str, default_tier: str = "terra", mutating: bool = False, override: str | None = None):
        if override:
            if override not in TIERS: raise ValueError("tier_override must be luna, terra, or sol")
            return override, {"reason": "explicit_override", "score": 0}
        text = prompt.strip(); score = 3
        if len(text) > 4000: score += 2
        elif len(text) > 1200: score += 1
        if self.HARD_TERMS.search(text): score += 2
        if self.LIGHT_TERMS.search(text): score -= 2
        if mutating: score += 1
        if any(x in text for x in ("```", "Traceback", "Exception", "stack trace")): score += 1
        if default_tier == "sol": score += 1
        elif default_tier == "luna": score -= 1
        return ("luna" if score <= 2 else "terra" if score <= 5 else "sol"), {"reason": "complexity_router", "score": score}
    def escalate(self, tier: str):
        try: idx = TIERS.index(tier)
        except ValueError: return None
        return TIERS[idx + 1] if idx + 1 < len(TIERS) else None
