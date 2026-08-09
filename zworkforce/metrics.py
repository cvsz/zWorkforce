from __future__ import annotations


def _label(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def prometheus(db, tenant_id: str) -> str:
    o = db.overview(tenant_id)
    lines = [
        "# HELP zworkforce_active_tasks Active queued/running/approval tasks.",
        "# TYPE zworkforce_active_tasks gauge",
        f"zworkforce_active_tasks {o['active_tasks']}",
        "# HELP zworkforce_queued_tasks Queued tasks.",
        "# TYPE zworkforce_queued_tasks gauge",
        f"zworkforce_queued_tasks {o['queued_tasks']}",
        "# HELP zworkforce_dead_letter_tasks Dead-letter tasks.",
        "# TYPE zworkforce_dead_letter_tasks gauge",
        f"zworkforce_dead_letter_tasks {o['dead_letter_tasks']}",
        "# HELP zworkforce_tasks_24h Tasks created in the last 24 hours.",
        "# TYPE zworkforce_tasks_24h gauge",
        f"zworkforce_tasks_24h {o['tasks_24h']}",
        "# HELP zworkforce_success_rate_24h Runtime success percentage.",
        "# TYPE zworkforce_success_rate_24h gauge",
        f"zworkforce_success_rate_24h {o['success_rate']}",
        "# HELP zworkforce_outcome_pass_rate_24h Business outcome pass percentage.",
        "# TYPE zworkforce_outcome_pass_rate_24h gauge",
        f"zworkforce_outcome_pass_rate_24h {o['outcome_pass_rate']}",
        "# HELP zworkforce_credits_24h Credits used in the last 24 hours.",
        "# TYPE zworkforce_credits_24h gauge",
        f"zworkforce_credits_24h {o['credits_24h']}",
        "# HELP zworkforce_cost_per_success_24h Credits per passed outcome.",
        "# TYPE zworkforce_cost_per_success_24h gauge",
        f"zworkforce_cost_per_success_24h {o['cost_per_success']}",
        "# HELP zworkforce_p95_duration_seconds_24h P95 task runtime.",
        "# TYPE zworkforce_p95_duration_seconds_24h gauge",
        f"zworkforce_p95_duration_seconds_24h {o['p95_duration_seconds']}",
    ]
    for row in o["model_mix"]:
        tier = _label(row["tier"])
        lines.append(f'zworkforce_model_turns_24h{{tier="{tier}"}} {row["turns"]}')
        lines.append(f'zworkforce_model_credits_24h{{tier="{tier}"}} {row["cost"]}')
    for row in o["provider_mix"]:
        provider = _label(row["provider_name"])
        lines.append(f'zworkforce_provider_turns_24h{{provider="{provider}"}} {row["turns"]}')
        lines.append(f'zworkforce_provider_credits_24h{{provider="{provider}"}} {row["cost"]}')
    for row in db.list_provider_health():
        provider = _label(row["name"])
        available = 1 if db.provider_available(row["name"]) else 0
        lines.append(f'zworkforce_provider_available{{provider="{provider}"}} {available}')
        lines.append(f'zworkforce_provider_failures_total{{provider="{provider}"}} {row["failures"]}')
        lines.append(f'zworkforce_provider_successes_total{{provider="{provider}"}} {row["successes"]}')
    return "\n".join(lines) + "\n"
