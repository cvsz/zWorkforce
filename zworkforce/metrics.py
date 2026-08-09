from __future__ import annotations

from .economics import slo_status


def _label(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def prometheus(db, tenant_id: str) -> str:
    o = db.overview(tenant_id)
    lines = [
        "# HELP zworkforce_active_tasks Active queued/running/approval tasks.", "# TYPE zworkforce_active_tasks gauge", f"zworkforce_active_tasks {o['active_tasks']}",
        "# HELP zworkforce_queued_tasks Queued tasks.", "# TYPE zworkforce_queued_tasks gauge", f"zworkforce_queued_tasks {o['queued_tasks']}",
        "# HELP zworkforce_dead_letter_tasks Dead-letter tasks.", "# TYPE zworkforce_dead_letter_tasks gauge", f"zworkforce_dead_letter_tasks {o['dead_letter_tasks']}",
        "# HELP zworkforce_tasks_24h Tasks created in the last 24 hours.", "# TYPE zworkforce_tasks_24h gauge", f"zworkforce_tasks_24h {o['tasks_24h']}",
        "# HELP zworkforce_success_rate_24h Runtime success percentage.", "# TYPE zworkforce_success_rate_24h gauge", f"zworkforce_success_rate_24h {o['success_rate']}",
        "# HELP zworkforce_outcome_pass_rate_24h Business outcome pass percentage.", "# TYPE zworkforce_outcome_pass_rate_24h gauge", f"zworkforce_outcome_pass_rate_24h {o['outcome_pass_rate']}",
        "# HELP zworkforce_credits_24h Credits used in the last 24 hours.", "# TYPE zworkforce_credits_24h gauge", f"zworkforce_credits_24h {o['credits_24h']}",
        "# HELP zworkforce_cost_per_success_24h Credits per passed outcome.", "# TYPE zworkforce_cost_per_success_24h gauge", f"zworkforce_cost_per_success_24h {o['cost_per_success']}",
        "# HELP zworkforce_p95_duration_seconds_24h P95 task runtime.", "# TYPE zworkforce_p95_duration_seconds_24h gauge", f"zworkforce_p95_duration_seconds_24h {o['p95_duration_seconds']}",
    ]
    for row in o["model_mix"]:
        tier = _label(row["tier"]); lines.append(f'zworkforce_model_turns_24h{{tier="{tier}"}} {row["turns"]}'); lines.append(f'zworkforce_model_credits_24h{{tier="{tier}"}} {row["cost"]}')
    for row in o["provider_mix"]:
        provider = _label(row["provider_name"]); lines.append(f'zworkforce_provider_turns_24h{{provider="{provider}"}} {row["turns"]}'); lines.append(f'zworkforce_provider_credits_24h{{provider="{provider}"}} {row["cost"]}')
    for row in db.list_provider_health():
        provider = _label(row["name"]); available = 1 if db.provider_available(row["name"]) else 0
        lines.append(f'zworkforce_provider_available{{provider="{provider}"}} {available}'); lines.append(f'zworkforce_provider_failures_total{{provider="{provider}"}} {row["failures"]}'); lines.append(f'zworkforce_provider_successes_total{{provider="{provider}"}} {row["successes"]}')
    with db.connection() as c:
        workflows = c.execute("SELECT COUNT(*) n FROM workflow_runs3 WHERE tenant_id=? AND status='running'", (tenant_id,)).fetchone()
        schedules = c.execute("SELECT COUNT(*) n FROM schedules3 WHERE tenant_id=? AND enabled=1", (tenant_id,)).fetchone()
        evals = c.execute("SELECT COUNT(*) n FROM evaluation_runs3 WHERE tenant_id=? AND status='running'", (tenant_id,)).fetchone()
        outbox = c.execute("SELECT COUNT(*) n FROM outbox3 WHERE tenant_id=? AND status='pending'", (tenant_id,)).fetchone()
    lines += [
        "# HELP zworkforce_workflow_runs_active Active workflow DAG runs.", "# TYPE zworkforce_workflow_runs_active gauge", f"zworkforce_workflow_runs_active {workflows['n']}",
        "# HELP zworkforce_schedules_enabled Enabled schedules.", "# TYPE zworkforce_schedules_enabled gauge", f"zworkforce_schedules_enabled {schedules['n']}",
        "# HELP zworkforce_evaluations_active Active evaluation runs.", "# TYPE zworkforce_evaluations_active gauge", f"zworkforce_evaluations_active {evals['n']}",
        "# HELP zworkforce_outbox_pending Pending integration outbox deliveries.", "# TYPE zworkforce_outbox_pending gauge", f"zworkforce_outbox_pending {outbox['n']}",
    ]
    for policy in slo_status(db, tenant_id).get("policies", []):
        pid = _label(policy["id"]); metric = _label(policy["metric"])
        lines.append(f'zworkforce_slo_value{{policy="{pid}",metric="{metric}"}} {policy["value"]}')
        lines.append(f'zworkforce_slo_ok{{policy="{pid}",metric="{metric}"}} {1 if policy["ok"] else 0}')
    return "\n".join(lines) + "\n"
