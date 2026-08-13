# zWorkforce Production Readiness Execution Plan

**Updated:** 2026-08-13
**Scope:** track the current v3.0.2 release baseline, post-release repository
hardening on `main`, and the remaining operator evidence required before a
real PostgreSQL-backed production promotion.

This is a production-readiness execution plan, not a claim that the operator
environment already exists. Repository CI proves source behavior and release
automation. PostgreSQL HA, identity, secrets, ingress/egress, artifact/vector
stores, observability, backups, signing material, branch protection, and
incident ownership still require environment-specific operator evidence.

## Current repository baseline

- Released tag: signed immutable `v3.0.2` points at
  `f56544ba58281e910dfa2132829f79992afa2a50`.
- Current `main` and `origin/main` point at
  `0eb525d3ba84a54c48315912f135819504b48c9a`.
- Post-release hardening merged after the `v3.0.2` tag:
  - PR #56 pruned the Z.A.R.V.I.S. package boundary and removed duplicated or
    obsolete product surfaces.
  - PR #57 hardened cross-platform validation, including Windows ACL
    enforcement for generated API-key secret files.
  - PR #58 fixed release publishing when optional trusted Windows MSIX
    artifacts are skipped.
  - PR #59 added the GitHub operations runbook and documentation coverage
    tests.
- Remote branch state is clean: `origin/main` is the only remote branch.
- Local validation for the latest `main` has passed with `102` unit/integration
  tests and `6` PostgreSQL tests skipped when no external PostgreSQL URL is
  configured.

The next public release should be a new patch tag after deciding whether the
post-release hardening changes should ship as `v3.0.3`.

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
7. Generated API-key secret files are not printed to stdout and are protected by
   mode `0600` on POSIX or owner-only ACLs on Windows.
8. Release publishing must succeed without Windows MSIX assets when trusted
   signing secrets are absent, but invalid signing material must fail closed.

## Repository work completed on `main`

- Schema v4 additions for workflow occurrence keys and outbox claim owner/expiry
  are covered by SQLite and PostgreSQL migration tests.
- Tenant isolation rejects cross-tenant memory ID collisions and preserves
  tenant ownership across memory/vector paths.
- Workflow dispatch accepts schedule/event occurrence keys and enforces stable
  `(tenant_id, idempotency_key)` behavior.
- Outbox delivery uses claimed rows, owner-checked completion, retry backoff,
  and reclaim tests.
- `/api/v1/scheduler-tick` passes an explicit scheduler owner and is covered by
  HTTP tests.
- Production startup rejects mock-only provider configuration.
- Windows secret-file output now enforces platform-specific permissions instead
  of skipping the Windows protection check.
- Release automation handles optional Windows artifacts and documents the
  trusted-signing boundary.
- GitHub operational documentation now covers branch policy, required checks,
  Dependabot, alert triage, releases, GHCR packages, and cleanup.

## Remaining repository backlog

These are not blockers for the current `main` tests, but they should be planned
before the next release or a real production launch:

1. Decide whether PR #57-#59 should be released as `v3.0.3`; if yes, update
   `CHANGELOG.md`, version metadata, Compose/Kubernetes references, and publish
   a new immutable tag.
2. Add a markdown link checker or documentation linter to CI so broken internal
   links fail pull requests.
3. Add a dedicated workflow/documentation test for required branch protection
   names once the GitHub ruleset is exported or represented as code.
4. Extend release verification to assert the GitHub operations runbook exists
   and mentions every required package-publishing path.
5. Run and record a live PostgreSQL integration suite outside GitHub's ephemeral
   service before staging promotion.

## Operator stages before production promotion

### Stage 1: Choose the database cutover posture

New production deployments use a fresh PostgreSQL database initialized by the
released image. SQLite remains supported for local development.

If an existing SQLite deployment contains data, promotion is blocked until a
separate, approved migration project supplies an export/import procedure. That
procedure must freeze writes, preserve all tenant-scoped tables and audit
chains, verify source/target counts and hashes, rehearse rollback, and record
the exact cutover.

### Stage 2: Provision production-equivalent staging

Configure and evidence:

- PostgreSQL TLS, least-privilege role, backups, PITR/retention, and restore;
- OIDC or signed proxy identity, tenant mapping, and four-eyes approvals;
- provider credentials and explicit model IDs, with no mock provider;
- secret-file, Vault, or AWS references and rotation ownership;
- default-deny egress for PostgreSQL, provider, OIDC/JWKS, OTLP, artifact,
  vector, and approved tool endpoints;
- immutable image reference, artifact storage, vector storage, metrics, logs,
  traces, alert routing, and cost budgets;
- GitHub branch/ruleset state, required checks, CodeQL, Dependency Review,
  Dependabot, secret scanning, package retention, and release access;
- trusted Windows MSIX signing secrets if Windows packages are part of the
  production release.

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
9. Trigger or dry-run release automation with and without Windows signing
   secrets; verify non-Windows assets publish when MSIX signing is absent.

### Stage 4: Controlled rollout

Promote only after hardening tests, staging drills, release artifact checks,
backup/restore evidence, identity/network review, GitHub operations review, and
owner sign-offs are attached to the change record. Start with a bounded
tenant/traffic cohort, monitor queue age, lease recovery, provider health,
outbox pending count, failure/dead-letter rate, and audit-chain errors, then
expand on explicit rollback criteria.

### Stage 5: Recurring operations

Track credential rotation, backup restore cadence, dependency updates, image
releases, GHCR package cleanup, GitHub alert triage, branch/ruleset changes,
alert ownership, cost budgets, RPO/RTO results, and incident actions. Re-audit
the at-least-once boundaries whenever a provider, mutating tool, scheduler
target, or external outbox consumer changes.

## Validation matrix

### Repository-local

```bash
python -m compileall -q zworkforce tests scripts
python -m unittest discover -s tests -v
python scripts/verify_release.py --expected 3.0.2
bash -n setup.sh scripts/*.sh packages/zarvis/scripts/*.sh packages/zarvis/scripts/git-gpg/*.sh packages/zarvis/services/voice-agent/entrypoint.sh
pnpm --dir packages/zarvis install --frozen-lockfile
pnpm --dir packages/zarvis peers check
pnpm --dir packages/zarvis test
pnpm --dir packages/zarvis audit --audit-level high
ZWORKFORCE_TEST_POSTGRES_URL="${ZWORKFORCE_TEST_POSTGRES_URL:?set a real PostgreSQL URL}" PYTHONPATH=. python -m unittest tests.test_v3_postgres -v
docker build --build-arg VERSION=3.0.2 -t zworkforce:3.0.2 .
```

The PostgreSQL command requires a real service. A skipped PostgreSQL suite is
not PostgreSQL evidence. Docker and package commands require the corresponding
local runtimes.

### Remote and operator-owned

- Confirm the intended release tag is signed, immutable, and an ancestor of
  protected `main`.
- Confirm required checks, CodeQL, Dependency Review, artifact checksums, SBOM,
  provenance, package contents, and image digest through GitHub.
- Confirm release behavior with optional Windows artifacts through workflow
  logs before claiming MSIX support for a release.
- Capture staging doctor output, live smoke output, migration posture, backup
  restore output, failure-drill results, alert routing, and sign-offs.

## Completion criteria

Repository readiness for the current `main` is complete when local full tests,
release verification, package audits, shell syntax checks, and GitHub Actions
are green for the candidate commit; documentation links cover operational
surfaces; production examples cannot start with mock providers; scheduler,
workflow, outbox, tenant isolation, secret-file protection, and release
publishing regressions remain covered.

Production readiness is complete only after the operator stages provide evidence
for the exact immutable image, PostgreSQL state, configuration revision,
identity/network controls, recovery drills, GitHub repository controls, package
retention, RPO/RTO, owners, and rollback path.
