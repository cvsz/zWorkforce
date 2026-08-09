# zWorkforce Production Readiness Execution Plan

**Updated:** 2026-08-09
**Scope:** harden the released v3.0.1 repository and define the operator evidence
required for a real PostgreSQL-backed production deployment.

This is a post-release plan. The v3.0.1 repository closure and release work are
completed evidence, not pending Sprint 0/1 tasks. External PostgreSQL, identity,
secret, network, artifact/vector, observability, backup, and GitHub settings are
operator-owned prerequisites and are not claimed to exist because manifests are
present. A native Windows client is a separate product effort.

## Verified release baseline

- `main`, `origin/main`, and the signed immutable `v3.0.1` tag point at
  `d5c0655c1ae343334e2ef2dc17f770e76461ee82`.
- `v3.0.0` remains unchanged at `1425192f9f544683b37352032298138c8b36b519`.
- Repository release metadata, package references, image references, security
  documentation, `make check`, and the repeatable PostgreSQL fixture were
  closed in the v3.0.1 release change.
- The public release record and CI summary must be rechecked through GitHub for
  every future promotion; local tests do not prove remote CodeQL, branch
  protection, artifact, or image-digest state.

## Architecture invariants

1. Memory IDs are tenant-owned. A caller-provided ID may update only the same
   tenant; a collision with another tenant is rejected, and vector joins carry
   the same tenant predicate.
2. Every scheduler schedule occurrence and event/rule occurrence has one stable
   idempotency key. Re-running dispatch after a crash returns the existing
   workflow run or task instead of creating another durable occurrence.
3. Queue workers and provider/tool calls are **at-least-once** after lease
   expiry. The repository does not claim exactly-once external side effects.
   Mutating tools and providers must tolerate retries or use their own
   idempotency key/fencing mechanism.
4. Outbox workers claim individual rows with an owner and expiry. Delivery sends
   `X-ZWorkforce-Delivery-ID`; consumers must deduplicate that ID because a
   process crash after a successful HTTP request and before completion recording
   is still a valid duplicate-delivery window.
5. Production configuration rejects mock providers. Compose and Kubernetes
   examples select an OpenAI-compatible provider and fail startup until real
   credentials are supplied.
6. `/ready` and `doctor` require a ready database, workspace, valid audit chain,
   and an available non-mock production provider. They do not replace an
   authenticated live-generation smoke test.

## Repository hardening tranche

The following changes are required in the release branch before any staging
drill:

- **Schema v4:** add workflow occurrence keys and outbox claim-owner/expiry
  columns with an additive migration for existing SQLite and PostgreSQL
  schemas.
- **Tenant isolation:** reject cross-tenant memory ID collisions, preserve the
  owning tenant on updates, validate vector ownership, and test the HTTP write
  path.
- **Workflow dispatch:** pass schedule/event keys into workflow-run creation;
  enforce a unique `(tenant_id, idempotency_key)` boundary and accept the same
  key on `POST /api/v1/workflow-runs`.
- **Outbox recovery:** claim rows before delivery, require the claim owner to
  finish them, release failed claims back to `pending`, and test exclusive
  claim/reclaim behavior.
- **Control-plane route:** make `/api/v1/scheduler-tick` pass an explicit
  scheduler owner accepted by `Scheduler.loop` and cover it with an HTTP test.
- **Production gate:** reject mock providers in both legacy and JSON provider
  configuration, remove mock defaults from production examples, and make
  readiness/doctor checks fail closed.

## Operator stages after the hardening tranche

### Stage 1: Choose the database cutover posture

New production deployments use a fresh PostgreSQL database initialized by the
released image. SQLite remains supported for local development.

If an existing SQLite deployment contains data, promotion is blocked until a
separate, approved migration project supplies an export/import procedure. That
procedure must freeze writes, preserve all tenant-scoped tables and audit
chains, verify source/target counts and hashes, rehearse rollback, and record
the exact cutover. This repository deliberately does not pretend to perform a
cross-backend data migration automatically.

### Stage 2: Provision production-equivalent staging

Configure and evidence:

- PostgreSQL TLS, least-privilege role, backups, PITR/retention, and restore;
- OIDC or signed proxy identity, tenant mapping, and four-eyes approvals;
- provider credentials and explicit model IDs, with no mock provider;
- secret-file/Vault/AWS references and rotation ownership;
- default-deny egress for PostgreSQL, provider, OIDC/JWKS, OTLP, artifact,
  vector, and approved tool endpoints;
- immutable image reference, artifact storage, vector storage, metrics, logs,
  traces, alert routing, and cost budgets.

Record the environment identifier, image digest, database snapshot identifier,
configuration revision, owners, RPO/RTO, and incident contacts together.

### Stage 3: Run failure and recovery drills

Run each drill against staging and attach command output or dashboard evidence:

1. Submit the same task and workflow occurrence twice with the same key; verify
   one durable task/run.
2. Crash a worker after claim; verify lease recovery and document the
   at-least-once side-effect boundary.
3. Run two schedulers and two outbox replicas; verify only one active claim per
   item while leases are valid.
4. Crash outbox after the HTTP request; verify a retry carries the same delivery
   ID and the consumer deduplicates it.
5. Exercise approval, rejection, cancellation, retry, tenant collision, and
   cross-tenant read/write denial paths.
6. Fail the primary provider, verify circuit opening/failover, then restore it.
7. Restore a PostgreSQL backup into an isolated target and run doctor plus the
   authenticated smoke test.
8. Redeploy the previous immutable image and verify schema/data compatibility;
   do not restore data solely to roll back a compatible application image.

### Stage 4: Controlled rollout

Promote only after the hardening tests, staging drills, release artifact checks,
backup/restore evidence, identity/network review, and owner sign-offs are
attached to the change record. Start with a bounded tenant/traffic cohort,
monitor queue age, lease recovery, provider health, outbox pending count,
failure/dead-letter rate, and audit-chain errors, then expand on explicit
rollback criteria.

### Stage 5: Recurring operations

Track credential rotation, backup restore cadence, dependency updates, image
releases, alert ownership, cost budgets, RPO/RTO results, and incident actions.
Re-audit the at-least-once boundaries whenever a provider, mutating tool,
scheduler target, or external outbox consumer changes.

## Validation matrix

### Repository-local

```bash
make check
PYTHONPATH=.:tests python3 -m unittest tests.test_production_fixes -v
ZWORKFORCE_TEST_POSTGRES_URL="${ZWORKFORCE_TEST_POSTGRES_URL:?set a real PostgreSQL URL}" PYTHONPATH=. python3 -m unittest tests.test_v3_postgres -v
ZWORKFORCE_TEST_POSTGRES_URL="${ZWORKFORCE_TEST_POSTGRES_URL:?set a real PostgreSQL URL}" PYTHONPATH=. python3 -m unittest tests.test_v3_postgres -v
docker build --build-arg VERSION=3.0.1 -t zworkforce:3.0.1 .
```

The PostgreSQL commands require a real service. A skipped PostgreSQL suite is
not PostgreSQL evidence. The Docker command requires access to a Docker daemon.

### Remote and operator-owned

- Confirm the release tag is signed, immutable, and an ancestor of protected
  `main`.
- Confirm required checks, CodeQL, dependency review, artifact checksums, SBOM,
  provenance, package contents, and image digest through GitHub.
- Capture staging doctor output, live smoke output, migration posture, backup
  restore output, failure-drill results, alert routing, and sign-offs.

## Completion criteria

Repository work is complete when all focused regressions and `make check` pass,
the production examples cannot start with mock providers, the scheduler HTTP
route works, tenant collisions are rejected, workflow occurrences are unique,
outbox claims are exclusive, and the plan’s at-least-once wording matches the
implementation.

Production readiness is complete only after the operator stages provide evidence
for the exact immutable image, PostgreSQL state, configuration revision,
identity/network controls, recovery drills, RPO/RTO, owners, and rollback path.
