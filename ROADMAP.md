# Roadmap

## v1.0.0 — completed
Single-node control plane, agents, model routing, approvals, tools, cost ledger, dashboard, Docker and CI.

## v2.0.0 — completed
Tenant isolation, durable SQLite lease workers, multi-provider failover, scoped persistent API keys, four-eyes approvals, per-agent grants, memory, signed skills, tamper-evident audit, outcome economics and hardened operations.

## v3.0.0 — completed in this release

- PostgreSQL distributed state and `SKIP LOCKED` worker leasing.
- Versioned workflow DAGs.
- Cron/interval scheduling and durable event triggers.
- Service leader leases for scheduler/outbox HA.
- Policy-as-code task/tool enforcement.
- A/B tier evaluation and model optimization evidence.
- Native OIDC and group-role mapping.
- Vault/AWS/file/env secret references.
- Stateless MCP 2026-07-28 management endpoint/client.
- Local/S3 content-addressed artifacts.
- Local/Qdrant semantic memory with OpenAI-compatible embeddings.
- OTLP tracing, Prometheus/Grafana examples.
- SLOs, capacity forecasts, chargeback/showback.
- Agent templates and semantic version snapshots.
- Signed remote skill registry.
- Kubernetes API/worker scaling, PDBs and network-policy baseline.

## Infrastructure adapters / future compatibility

These are intentionally external deployment concerns rather than fake in-process features:

- managed PostgreSQL HA / PITR / multi-region replication;
- organization-specific SAML/SCIM lifecycle through an IdP or identity-aware proxy;
- provider-specific managed queues when PostgreSQL leasing is not the desired queue;
- organization-specific SaaS connectors, exposed safely through MCP or approved internal gateways;
- cloud-specific ingress, WAF, KMS/HSM, service mesh and egress proxy configuration;
- disaster-recovery runbooks tied to the operator's cloud and RPO/RTO.

The platform boundary remains extensible, but v3 does not claim external infrastructure has been provisioned when credentials/accounts are not present.
