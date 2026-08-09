# Data Model

Core v2 tables:

- `tenants` — tenant registry.
- `agents2` — tenant-scoped agent policy/configuration.
- `tasks2` — task state, leases, attempts, usage totals and outcome result.
- `task_events2` — ordered lifecycle events.
- `approvals2` — unique actor decisions per task.
- `usage_events2` — per-model-turn provider/model/tier/token/credit ledger.
- `budgets2` — tenant/global/department/agent limits.
- `idempotency_keys2` — tenant + actor scoped client retry keys with request hash.
- `audit_events2` — tamper-evident tenant audit chain.
- `api_keys2` — hashed control-plane credentials and scopes.
- `memories2` — tenant/agent-scoped knowledge records.
- `skills2` — signed declarative skill manifests.
- `tool_events2` — tool audit, latency and success data.
- `provider_health2` — persistent circuit-breaker observations.

Legacy v1 tables are retained after safe-copy migration for rollback/forensics.
