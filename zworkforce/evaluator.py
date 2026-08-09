from __future__ import annotations

import json
import re
from typing import Any


class EvaluationError(ValueError):
    pass


def evaluate(content: str, criteria: list[dict[str, Any]] | None) -> tuple[str, float, dict[str, Any]]:
    criteria = criteria or [{"type": "non_empty"}]
    checks: list[dict[str, Any]] = []
    passed = 0
    for raw in criteria:
        if not isinstance(raw, dict):
            raise EvaluationError("success criteria must be objects")
        kind = str(raw.get("type", "")).strip().lower()
        ok = False
        detail: dict[str, Any] = {"type": kind}
        if kind == "non_empty":
            ok = bool(content.strip())
        elif kind == "contains":
            value = str(raw.get("value", ""))
            if not value:
                raise EvaluationError("contains criterion requires value")
            ok = value in content
            detail["value"] = value[:200]
        elif kind == "regex":
            pattern = str(raw.get("pattern", ""))
            if not pattern or len(pattern) > 500:
                raise EvaluationError("regex criterion requires a pattern up to 500 characters")
            try:
                ok = bool(re.search(pattern, content, flags=re.MULTILINE))
            except re.error as exc:
                raise EvaluationError(f"invalid regex criterion: {exc}") from exc
            detail["pattern"] = pattern
        elif kind == "json":
            try:
                json.loads(content)
                ok = True
            except json.JSONDecodeError:
                ok = False
        elif kind == "max_chars":
            value = int(raw.get("value", 0))
            if value <= 0:
                raise EvaluationError("max_chars criterion requires positive value")
            ok = len(content) <= value
            detail["value"] = value
        else:
            raise EvaluationError(f"unsupported success criterion: {kind}")
        detail["passed"] = ok
        checks.append(detail)
        passed += int(ok)
    score = passed / len(checks) if checks else 0.0
    return ("passed" if passed == len(checks) else "failed", round(score, 6), {"checks": checks})
