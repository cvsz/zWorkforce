from __future__ import annotations

from datetime import datetime, timezone, timedelta
import math
from typing import Any


def chargeback_report(db, tenant_id: str, hours: int = 720) -> dict[str, Any]:
    economics = db.get_tenant_economics(tenant_id)
    summary = db.usage_summary(tenant_id, hours)
    amount = float(summary["credits"]) * float(economics["currency_per_credit"])
    return {
        "tenant_id": tenant_id,
        "window_hours": max(1, int(hours)),
        "credits": round(float(summary["credits"]), 6),
        "currency": economics["currency"],
        "currency_per_credit": float(economics["currency_per_credit"]),
        "chargeback_amount": round(amount, 6),
        "tasks": summary["tasks"],
        "successful_tasks": summary["succeeded"],
        "cost_per_successful_task": round(amount / max(1, int(summary["succeeded"])), 6),
    }


def capacity_forecast(db, tenant_id: str, hours: int = 24, target_utilization: float | None = None) -> dict[str, Any]:
    hours = max(1, int(hours))
    economics = db.get_tenant_economics(tenant_id)
    target = max(.1, min(float(target_utilization or economics["target_worker_utilization"]), .95))
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="seconds")
    with db.connection() as c:
        rows = c.execute(
            "SELECT started_at,finished_at FROM tasks2 WHERE tenant_id=? AND created_at>=?",
            (tenant_id, since),
        ).fetchall()
    total = len(rows)
    durations = [max(0.0, _duration_ms(r["started_at"], r["finished_at"]) / 1000.0)
                 for r in rows if r["started_at"] and r["finished_at"]]
    avg_seconds = sum(durations) / max(1, len(durations))
    arrival_per_hour = total / hours
    service_hours_per_hour = arrival_per_hour * avg_seconds / 3600.0
    workers = max(1, math.ceil(service_hours_per_hour / target)) if total else 1
    return {
        "tenant_id": tenant_id,
        "window_hours": hours,
        "tasks_observed": total,
        "arrival_rate_per_hour": round(arrival_per_hour, 6),
        "avg_service_seconds": round(avg_seconds, 3),
        "target_utilization": target,
        "recommended_workers": workers,
        "note": "Forecast is demand-based and should be combined with provider concurrency/rate-limit constraints.",
    }


def slo_status(db, tenant_id: str) -> dict[str, Any]:
    policies = db.list_slo_policies(tenant_id)
    results = []
    for policy in policies:
        if not policy.get("enabled"):
            continue
        hours = max(1, int(policy.get("window_hours", 24)))
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="seconds")
        metric = policy["metric"]
        with db.connection() as c:
            total = int(c.execute("SELECT COUNT(*) n FROM tasks2 WHERE tenant_id=? AND created_at>=?", (tenant_id, since)).fetchone()["n"])
            if metric == "success_rate":
                good = int(c.execute("SELECT COUNT(*) n FROM tasks2 WHERE tenant_id=? AND created_at>=? AND status='succeeded'", (tenant_id, since)).fetchone()["n"])
                value = good / max(1, total)
            elif metric == "outcome_rate":
                good = int(c.execute("SELECT COUNT(*) n FROM tasks2 WHERE tenant_id=? AND created_at>=? AND outcome_status='passed'", (tenant_id, since)).fetchone()["n"])
                value = good / max(1, total)
            elif metric == "dead_letter_rate":
                bad = int(c.execute("SELECT COUNT(*) n FROM tasks2 WHERE tenant_id=? AND created_at>=? AND status='dead_letter'", (tenant_id, since)).fetchone()["n"])
                value = bad / max(1, total)
            elif metric == "p95_duration_ms":
                rows = c.execute("SELECT started_at,finished_at FROM tasks2 WHERE tenant_id=? AND created_at>=? AND started_at IS NOT NULL AND finished_at IS NOT NULL", (tenant_id, since)).fetchall()
                vals = sorted(_duration_ms(r["started_at"], r["finished_at"]) for r in rows)
                value = vals[min(len(vals)-1, math.ceil(.95 * len(vals))-1)] if vals else 0.0
            elif metric == "avg_queue_ms":
                rows = c.execute("SELECT created_at,started_at FROM tasks2 WHERE tenant_id=? AND created_at>=? AND started_at IS NOT NULL", (tenant_id, since)).fetchall()
                vals = [_duration_ms(r["created_at"], r["started_at"]) for r in rows]
                value = sum(vals) / max(1, len(vals))
            else:
                continue
        target = float(policy["target"])
        ok = value >= target if policy["comparator"] == "gte" else value <= target
        results.append({"id": policy["id"], "metric": metric, "value": round(float(value), 6), "target": target,
                        "comparator": policy["comparator"], "ok": ok, "severity": policy["severity"], "window_hours": hours})
    return {"tenant_id": tenant_id, "ok": all(x["ok"] for x in results), "policies": results}


def _duration_ms(start: str, end: str) -> float:
    try:
        return max(0.0, (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() * 1000)
    except (TypeError, ValueError):
        return 0.0
