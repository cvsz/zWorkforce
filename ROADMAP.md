# Roadmap

## v2.0.0 — implemented

- Multi-tenant v2 data model and v1 safe-copy migration
- Persistent scoped API keys and superadmin tenant switching
- Durable queue leases, heartbeats, stale recovery, retries and dead-letter
- Separate API/worker process modes
- Health-aware multi-provider priority/fallback/circuit breaking
- Per-agent tool grants and approval-sensitive mutations
- Distinct/four-eyes approvals
- Hardened workspace, HTTP, shell and memory tools
- Signed skill manifests and tenant memory retrieval
- Tamper-evident audit hash chain
- Deterministic outcome evaluators, cost per success and rightsizing signals
- Expanded dashboard, metrics, Docker/Compose, docs and CI on Python 3.12–3.14

## Next backend adapters

Infrastructure-dependent work intentionally not represented as completed guarantees:

- PostgreSQL repository + `SKIP LOCKED` leases for cross-host worker fleets
- Managed queue adapters such as SQS, Pub/Sub, Kafka or Redis Streams
- OTLP trace exporter and external immutable audit sink
- Dedicated OIDC/SAML/SCIM adapters where identity does not terminate at an identity-aware proxy
- Object/vector stores for large memory/RAG corpora
- Multi-region scheduler, placement and data-residency policy
- Secret-manager adapters and key-rotation orchestration

## Product evolution

- Workflow DAGs and scheduled/event-triggered tasks
- Evaluation suites and A/B model routing
- Provider price synchronization and chargeback currency
- Approval inbox integrations
- Signed remote skill/package distribution
- Organization-level SLOs and capacity forecasting
