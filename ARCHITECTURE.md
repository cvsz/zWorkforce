# Architecture — zWorkforce v2.0

## Goals

zWorkforce provides a dependency-light control plane for governed AI agents. The runtime optimizes for correctness, bounded execution, recoverability, auditability and cost visibility before autonomy.

## Components

### Control plane

The HTTP server owns authentication, tenant resolution, RBAC/scopes, rate limiting, agent policy, budget configuration, memory, skills, audit inspection and task lifecycle actions. Static dashboard assets contain no provider credentials.

### Durable task repository

SQLite runs in WAL mode with `busy_timeout` and explicit `BEGIN IMMEDIATE` transactions around queue claims, approvals and idempotency. v2 tables are tenant-aware and coexist with untouched v1 tables for migration safety.

### Worker runtime

Workers transactionally claim one queued task, mark it running, increment its attempt number and write a lease owner/expiry. A heartbeat thread extends the lease while provider/tool turns execute. Expired leases are requeued unless attempts are exhausted, then the task becomes `dead_letter`.

### Provider pool

Providers define priority, type, endpoint, tier-to-model mapping, timeout and retry policy. Real calls update persistent health. Consecutive failures open a temporary circuit; calls fall through to the next healthy provider that supports the tier.

### Policy/tool gateway

The worker exposes only agent-granted tool schemas. Models cannot execute ungranted capabilities by naming them. Mutating tools additionally require a mutating task and completed approvals when policy requires them.

### AI FinOps and outcome evaluation

Every model turn records provider, model, tier, tokens and computed credits. Deterministic outcome criteria are evaluated after runtime completion, separating `status=succeeded` from `outcome_status=passed`.

## State machine

`waiting_approval -> queued -> running -> succeeded|failed|canceled`

Retryable provider failures transition `running -> queued` with exponential `run_after`. Exhausted attempts or repeated lease expiry transition to `dead_letter`; failed/dead-letter tasks can be manually retried.

## Multi-tenancy

Tenant ID is present in all v2 policy/data tables. API keys bind to one tenant. Only `superadmin` can explicitly switch to another existing tenant using `X-Tenant-ID`. Worker execution derives tenant exclusively from the stored task.

## Audit integrity

Each tenant has an independent SHA-256 hash chain over canonicalized audit events. Verification recomputes every event. This detects ordinary in-database edits but does not replace external immutable storage against a fully privileged host attacker.

## Concurrency boundary

SQLite WAL supports multiple processes on one reliable local filesystem. The project does not claim multi-host HA over network filesystems. A transactional PostgreSQL/managed-queue backend is the correct next boundary for horizontal cross-host scale.
