# Changelog

## 3.0.1 — 2026-08-09

### Security and reliability
- Hardened response-header construction and fixed static MIME mappings.
- Replaced weak API-key verification with salted PBKDF2-HMAC-SHA256 records.
- Rejected legacy unsalted API-key records; operators must recreate and rotate
  those credentials before upgrading.
- Added secure mode-0600 CLI secret-file output without plaintext stdout leaks.
- Made PostgreSQL integration fixtures repeatable across test runs.

### Dependencies and operations
- Updated checkout, Python setup, Buildx, image build/push, registry login, and
  Python container dependencies.
- Protected `main` with pull-request, status-check, force-push, and deletion
  controls.

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
- Tag-driven GitHub release pipeline with wheel/sdist, SHA-256 checksums, CycloneDX SBOM, build provenance and GHCR OCI provenance/SBOM.
- Dependabot, dependency review, CODEOWNERS and pull-request security/release checklist.
- Production readiness, release, secret-management and disaster-recovery runbooks.
- Guarded PostgreSQL backup/restore scripts and deployment smoke test.
- Release metadata verifier enforcing package/Compose/Kubernetes version consistency.

### Changed
- Production Compose defaults to PostgreSQL with dedicated API/worker/scheduler services and supports immutable `ZWORKFORCE_IMAGE` overrides.
- Kubernetes release manifests use canonical `v3.0.0` GHCR tags.
- Python dependency floors updated for the v3 distributed/identity stack.
- Dashboard and API surface expanded for automation, evaluation and economics.
- CI now validates operational scripts, release metadata, SBOM generation and production Compose rendering in addition to runtime tests.

### Compatibility
- Existing v2 SQLite data/schema remains supported.
- Existing `/api/v1` task/agent/memory/provider endpoints remain available.

## 2.0.0 — 2026-08-09
Multi-tenant durable runtime, provider failover, scoped identity, approvals, tool policy, memory, signed skills, audit integrity, outcome economics and AI FinOps.

## 1.0.0 — 2026-08-09
Initial production-oriented single-node AI Workforce control plane.
