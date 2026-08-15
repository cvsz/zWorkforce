# Zeto Architecture

## Mission

Zeto is an AI content factory covering ideation, generation, approval, scheduling, publishing, monitoring, and learning. The intended module lifecycle is `PRODUCTION`, `OPS`, and `OPTIMIZE`.

## Current State

The v2 migration starts from a Node.js/Express SPA with a Facebook publishing integration. PostgreSQL migrations, transactional repositories, durable jobs, operational settings/pages/queue/history/sessions, and the initial `/v1/brands` API are implemented. The legacy `/api` HTTP contract remains for client compatibility, but its state is PostgreSQL-backed.

## Layers

1. **HTTP/API** — `/v1` routes, authentication, authorization, validation, idempotency and correlation IDs.
2. **Application services** — use cases and orchestration without transport or provider details.
3. **Domain/workflows** — content lifecycle, approvals, publication states and workflow state machines.
4. **Repositories** — persistence contracts; PostgreSQL is the production target.
5. **Providers** — AI models, publishing platforms and object storage behind stable interfaces.
6. **Workers** — durable asynchronous execution with retries, cancellation, deadlines and dead-letter handling.
7. **Observability** — structured logs, metrics, traces and immutable audit events.

## Canonical lifecycle

`IDEATE → GENERATE → WRITE → APPROVE → SCHEDULE → PUBLISH → MONITOR → LEARN`

## Target Boundaries

- `/v1` HTTP API: authentication, authorization, validation, idempotency, and stable response contracts.
- Domain services: strategy, generation, QA, approval, calendar, monitoring, analytics, and orchestration.
- PostgreSQL repositories: transactional state and immutable audit records.
- Durable jobs: retry, timeout, cancellation, ownership, heartbeats, and dead-letter semantics.
- Provider interfaces: model, object-storage, monitoring, and publishing adapters.
- Observability: structured logs, metrics, traces, alerts, and cost events.

## Critical Invariants

- Provider secrets stay server-side.
- Side effects are idempotent.
- Autonomous publishing cannot bypass QA, policy or budget limits.
- All mutations emit audit events.
- Platform-specific behavior lives in adapters.
- Every generated artifact retains provenance and version information.
- Analytics must be reproducible from persisted source data.
- Publishing requires an approved artifact and a transactional claim.
- `AUTO_PILOT` cannot bypass policy, budget, permission, frequency, or kill-switch controls.

## Migration Strategy

The current JSON-backed Facebook automation remains functional while behavior is moved behind repository and provider contracts. Migration proceeds by vertical slices rather than a big-bang rewrite. PostgreSQL becomes authoritative only after schema/migration tests and restart/idempotency tests pass.

Architectural decisions are recorded under `docs/adr/`.
