from __future__ import annotations

from collections import defaultdict
from typing import Any

from .db import TERMINAL_STATUSES


class EvaluationSuiteError(ValueError):
    pass


def validate_suite(suite: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(suite, dict):
        raise EvaluationSuiteError("suite must be an object")
    cases = suite.get("cases")
    variants = suite.get("variants")
    if not isinstance(cases, list) or not cases or len(cases) > 100:
        raise EvaluationSuiteError("suite cases must contain 1..100 cases")
    if not isinstance(variants, list) or len(variants) < 2 or len(variants) > 8:
        raise EvaluationSuiteError("suite variants must contain 2..8 variants")
    case_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise EvaluationSuiteError("evaluation case must be an object")
        cid = str(case.get("id", "")).strip()
        if not cid or cid in case_ids:
            raise EvaluationSuiteError("evaluation case ids must be unique and non-empty")
        case_ids.add(cid)
        if not str(case.get("prompt", "")).strip():
            raise EvaluationSuiteError(f"case {cid} requires prompt")
    variant_names: set[str] = set()
    for variant in variants:
        if not isinstance(variant, dict):
            raise EvaluationSuiteError("evaluation variant must be an object")
        name = str(variant.get("name", "")).strip()
        tier = str(variant.get("tier", "")).strip()
        if not name or name in variant_names:
            raise EvaluationSuiteError("variant names must be unique and non-empty")
        if tier not in {"luna", "terra", "sol"}:
            raise EvaluationSuiteError(f"variant {name} tier must be luna, terra, or sol")
        variant_names.add(name)
    return suite


class EvaluationRunner:
    def __init__(self, db, engine):
        self.db, self.engine = db, engine

    def upsert(self, tenant_id: str, suite: dict[str, Any], actor: str) -> dict[str, Any]:
        suite = validate_suite(dict(suite))
        return self.db.upsert_evaluation_suite(tenant_id, suite, actor)

    def start(self, tenant_id: str, suite_id: str, actor: str) -> dict[str, Any]:
        suite = self.db.get_evaluation_suite(tenant_id, suite_id)
        if not suite or not suite.get("enabled"):
            raise EvaluationSuiteError("evaluation suite not found or disabled")
        validate_suite(suite)
        run = self.db.create_evaluation_run(tenant_id, suite_id, actor)
        for case in suite["cases"]:
            for variant in suite["variants"]:
                task, _ = self.engine.submit(
                    tenant_id,
                    suite["agent_id"],
                    str(case["prompt"]),
                    actor=f"eval:{run['id']}",
                    mutating=False,
                    tier_override=variant["tier"],
                    success_criteria=case.get("success_criteria") or [{"type": "non_empty"}],
                    idempotency_key=f"eval:{run['id']}:{case['id']}:{variant['name']}",
                )
                self.db.add_evaluation_result(tenant_id, run["id"], str(case["id"]), str(variant["name"]), task["id"])
        return self.db.get_evaluation_run(tenant_id, run["id"]) or run

    def tick(self) -> dict[str, int]:
        runs = self.db.active_evaluation_runs()
        stats = {"runs": len(runs), "completed": 0}
        for run in runs:
            results = self.db.list_evaluation_results(run["id"])
            pending = False
            for item in results:
                if item["status"] in TERMINAL_STATUSES:
                    continue
                task = self.db.get_task(run["tenant_id"], item["task_id"])
                if not task or task["status"] not in TERMINAL_STATUSES:
                    pending = True
                    continue
                self.db.update_evaluation_result_from_task(item["id"], task)
            results = self.db.list_evaluation_results(run["id"])
            if pending or any(x["status"] not in TERMINAL_STATUSES for x in results):
                continue
            summary = self._summary(results)
            self.db.finish_evaluation_run(run["id"], "succeeded", summary)
            stats["completed"] += 1
        return stats

    @staticmethod
    def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in results:
            buckets[item["variant"]].append(item)
        variants = []
        for name, items in sorted(buckets.items()):
            total = len(items)
            passed = sum(1 for x in items if x.get("outcome_status") == "passed")
            score = sum(float(x.get("outcome_score") or 0) for x in items) / max(1, total)
            cost = sum(float(x.get("cost_credits") or 0) for x in items)
            duration = sum(float(x.get("duration_ms") or 0) for x in items) / max(1, total)
            variants.append({
                "name": name,
                "cases": total,
                "pass_rate": round(passed / max(1, total), 6),
                "avg_score": round(score, 6),
                "total_credits": round(cost, 6),
                "avg_duration_ms": round(duration, 3),
            })
        ranked = sorted(variants, key=lambda x: (-x["pass_rate"], -x["avg_score"], x["total_credits"], x["avg_duration_ms"]))
        return {"variants": variants, "recommended_variant": ranked[0]["name"] if ranked else None}
