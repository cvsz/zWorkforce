# Roadmap

This roadmap tracks shipped release lines and the next repository/operator
work. It does not claim that external production infrastructure exists merely
because manifests or configuration examples are present.

## v1.0.0 — completed

Single-node control plane, agents, model routing, approvals, tools, cost
ledger, dashboard, Docker and CI.

## v2.0.0 — completed

Tenant isolation, durable SQLite lease workers, multi-provider failover, scoped
persistent API keys, four-eyes approvals, per-agent grants, memory, signed
skills, tamper-evident audit, outcome economics and hardened operations.

## v3.0.0 — completed

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
- Tag-driven release workflow, SBOM, checksums, provenance, GHCR publishing,
  Dependabot, Dependency Review, CodeQL, and production runbooks.

## v3.0.1 — completed

- Hardened response-header construction and static MIME mappings.
- Replaced weak API-key verification with salted PBKDF2-HMAC-SHA256 records.
- Rejected legacy unsalted API-key records so operators must recreate and rotate
  those credentials before upgrading.
- Added secure CLI API-key secret-file output without plaintext stdout leaks.
- Made PostgreSQL integration fixtures repeatable.
- Protected `main` with pull-request, status-check, force-push, and deletion
  controls.

## v3.0.2 — completed

- Added the packaged Windows 11 operator client and Windows client CI.
- Enforced HTTPS for non-local client connections and protected API-key
  transport.
- Made MSIX smoke-test certificate trust cleanup deterministic.
- Documented the production Workforce control-plane endpoint.
- Consolidated Z.A.R.V.I.S. under `packages/zarvis` with package-level CI,
  release governance, API tests, Node workspace tests, and Windows restore
  checks.

## Current main — post-v3.0.2 hardening

- Pruned duplicated/obsolete Z.A.R.V.I.S. product surfaces from the consolidated
  package boundary.
- Enforced owner-only Windows ACLs for generated API-key secret files.
- Fixed release publishing when trusted Windows MSIX signing secrets are absent.
- Added `docs/GITHUB-OPERATIONS.md` for branch, check, alert, release, package,
  GHCR, and cleanup operations.
- Added `docs/PROMETA-MASTER.md` as the master agent, skill and prompt-metadata
  operating model.
- Refreshed `exec-planning.md` for the current `main` baseline and remaining
  production evidence.

## Candidate v3.0.3 backlog

- Decide whether current post-v3.0.2 hardening should ship as `v3.0.3`.
- Update version metadata, `CHANGELOG.md`, Compose/Kubernetes image references,
  and release notes for the new patch release.
- Add a markdown link checker or documentation linter to CI.
- Add repository ruleset or branch-protection evidence as code when GitHub
  settings are exported.
- Extend release verification to assert GitHub operations documentation coverage
  for every workflow and package-publishing path.
- Record a live PostgreSQL integration run against an operator-owned service,
  not only GitHub's ephemeral CI service.

## Infrastructure adapters / future compatibility

These remain external deployment concerns rather than fake in-process features:

- managed PostgreSQL HA, PITR, and multi-region replication;
- organization-specific SAML/SCIM lifecycle through an IdP or identity-aware
  proxy;
- provider-specific managed queues when PostgreSQL leasing is not the desired
  queue;
- organization-specific SaaS connectors exposed safely through MCP or approved
  internal gateways;
- cloud-specific ingress, WAF, KMS/HSM, service mesh and egress proxy
  configuration;
- disaster-recovery runbooks tied to the operator's cloud and RPO/RTO.

The platform boundary remains extensible, but zWorkforce does not claim external
infrastructure has been provisioned until credentials, accounts, controls,
drills and sign-offs are recorded for the exact deployment.
