# Architecture

## Invariants
1. Provider credentials never reach browser code.
2. Every task has a model tier, iteration ceiling, spend ceiling and agent policy.
3. Mutating work can be approval-gated before runtime execution.
4. File/network/process tools are bounded and deny-by-default where applicable.
5. Every provider turn records usage; every control-plane mutation records audit data.
6. Model aliases are policy names and resolve to provider IDs through configuration.

## Components
- `api.py` — HTTP/RBAC/dashboard boundary.
- `db.py` — SQLite/WAL repositories, usage ledger, budgets, idempotency and audit.
- `router.py` — complexity routing and escalation.
- `providers.py` — mock and OpenAI-compatible providers.
- `tools.py` — deterministic capability gateway.
- `engine.py` — task state machine, approvals, runtime loops, delegation and accounting.
- `metrics.py` — Prometheus exposition.

## State machine
```text
create -> waiting_approval -> queued -> running -> succeeded
               |                         |  \-> failed
               |                         \----> canceled
               \---------------- cancel ------> canceled
```

SQLite uses WAL and per-operation connections. Transactional creates use `BEGIN IMMEDIATE` to keep idempotency atomic. Worker concurrency is bounded by `ZWORKFORCE_MAX_WORKERS`.
