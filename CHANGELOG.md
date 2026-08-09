# Changelog

## 3.0.0 — 2026-08-09

### Added
- PostgreSQL distributed backend and `SKIP LOCKED` queue claims.
- Workflow DAGs, schedules, event rules and leader-elected scheduler.
- Policy-as-code runtime enforcement.
- A/B evaluation suites and model-tier optimization summaries.
- Native OIDC, secret-store references and signed remote skills.
- Stateless MCP management endpoint/client.
- Runtime-selectable local/S3 artifact stores.
- Runtime-selectable local/Qdrant semantic memory with embedding adapter.
- OTLP tracing, durable webhook outbox, SLO/capacity/chargeback reporting.
- Agent templates/version history, Kubernetes and observability deployment examples.

### Changed
- Production Compose defaults to PostgreSQL with dedicated API/worker/scheduler services.
- Python dependency floors updated for the v3 distributed/identity stack.
- Dashboard and API surface expanded for automation, evaluation and economics.

### Compatibility
- Existing v2 SQLite data/schema remains supported.
- Existing `/api/v1` task/agent/memory/provider endpoints remain available.

## 2.0.0 — 2026-08-09
Multi-tenant durable runtime, provider failover, scoped identity, approvals, tool policy, memory, signed skills, audit integrity, outcome economics and AI FinOps.

## 1.0.0 — 2026-08-09
Initial production-oriented single-node AI Workforce control plane.
