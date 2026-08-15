# zWorkforce Production Readiness Execution Plan

**Updated:** 2026-08-14  
**Candidate:** `v3.0.3` on `agent/exec-plan-v3.0.3-readiness`  
**Baseline main:** `456ebde0e2bebba1fd4355cb66cda8197065ac33`

This is a production-readiness execution plan, not a claim that the operator
environment already exists. Repository CI proves source behavior and release
automation. PostgreSQL HA/PITR, identity, secrets, ingress/egress,
artifact/vector stores, observability, backups, signing material, server-side
GitHub ruleset enforcement, and incident ownership still require
environment-specific operator evidence.

The durable evidence ledger for the candidate is
[`docs/PRODUCTION-EVIDENCE.md`](docs/PRODUCTION-EVIDENCE.md). Any external stage
without real evidence remains `PENDING EXTERNAL EVIDENCE`.

## Current repository baseline

- Last released baseline remains immutable tag `v3.0.2`.
- Current `main` baseline for this execution is
  `456ebde0e2bebba1fd4355cb66cda8197065ac33`, which includes the merged native
  WinUI frontend refresh from PR #67.
- `v3.0.3` is now the explicit next release candidate in package, module,
  dashboard, Makefile, Compose, Kubernetes, publication workflow, changelog,
  README, and release/deployment documentation on the candidate branch.
- The candidate branch adds a dedicated documentation/repository-policy check,
  an API-compatible desired-state GitHub ruleset contract, a production
  evidence ledger, and stronger release metadata verification.
- The exact final candidate SHA must be recorded only after all candidate edits
  are complete and CI is green; do not pre-record a moving branch tip.

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
9. A repository CI backup/restore drill is regression evidence, not proof of a
   managed production PostgreSQL backup, restore, PITR, RPO, or RTO.
10. A checked-in ruleset contract is desired state, not proof that the same
    rules are active in GitHub. Server-side reconciliation requires repository
    administration permission and must be recorded as evidence.

## Repository work completed before this candidate

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
- Windows secret-file output enforces platform-specific permissions.
- Release automation handles optional Windows artifacts and documents the
  trusted-signing boundary.
- GitHub operational documentation covers branch policy, checks, Dependabot,
  alert triage, releases, GHCR packages, and cleanup.
- PR #67 refreshed the native WinUI shell and Overview presentation while
  preserving API/event/view-model contracts.

## v3.0.3 repository backlog execution

| Item from the previous plan | Candidate status | Evidence / implementation |
| --- | --- | --- |
| Decide and prepare `v3.0.3` | **DONE — candidate prepared** | `pyproject.toml`, `zworkforce/__init__.py`, `Makefile`, dashboard, Compose, Kubernetes, `publish-container.yml`, README, release/deployment docs, and `CHANGELOG.md` align on `3.0.3`. Immutable tag is intentionally deferred until merge + release evidence. |
| Fail CI on broken Markdown/internal links | **DONE** | Existing documentation link coverage is promoted into dedicated `documentation-contract` CI and continues to run in the full unit suite. |
| Represent required branch-protection contexts as code and test names | **DONE repository-side** | `.github/rulesets/main.json` + `tests/test_repository_policy.py`; actual GitHub check names were verified from real PR check runs. Path-filtered ZARVIS jobs are intentionally excluded from global required contexts. |
| Extend release verifier for GitHub operations and package publishing | **DONE** | `scripts/verify_release.py` now checks the GitHub operations runbook, manual container publication guards, ruleset contract, evidence ledger, Makefile/dashboard/deploy versions, and mandatory release paths. |
| Run a live PostgreSQL suite outside GitHub's ephemeral service | **PENDING EXTERNAL EVIDENCE** | Must use a real staging/external PostgreSQL service and be recorded in `docs/PRODUCTION-EVIDENCE.md`. CI's PostgreSQL service and dump/restore drill do not satisfy this operator stage. |
| Reconcile desired ruleset with server-side GitHub enforcement | **PENDING ADMIN EVIDENCE** | The repository exposes the current server ruleset for inspection, but the available automation surface does not provide a ruleset mutation action. Apply/reconcile with GitHub repository administration permission and record the resulting ruleset URL/ID. |
| Create immutable `v3.0.3` tag and publish release | **BLOCKED BY DESIGN UNTIL GO** | Tag creation occurs only after candidate merge, all mandatory CI checks, required review, and production evidence/GO decision. |

## GitHub required-check design

Global required contexts in `.github/rulesets/main.json` are checks that are
expected for every pull request:

- `test (3.12)`
- `test (3.13)`
- `test (3.14)`
- `postgres-integration`
- `release-integrity`
- `container`
- `security-invariants`
- `documentation-contract`
- `dependency-review`
- `build-test-package`
- `Analyze (python)`
- `Analyze (actions)`
- `CodeQL`

`ZARVIS` is path-filtered. Its `migration-contract`, `node-workspace`,
`zarvis-api`, and `zarvis-windows-linux-restore` jobs are mandatory when the
workflow is triggered, but they must not be global required contexts or an
unrelated PR could remain permanently blocked waiting for jobs that were never
created.

## Operator stages before production promotion

### Stage 1: Choose the database cutover posture

New production deployments use a fresh PostgreSQL database initialized by the
released image. SQLite remains supported for local development.

If an existing SQLite deployment contains data, promotion is blocked until a
separate, approved migration project supplies an export/import procedure. That
procedure must freeze writes, preserve all tenant-scoped tables and audit
chains, verify source/target counts and hashes, rehearse rollback, and record
the exact cutover.

**Status:** `PENDING EXTERNAL EVIDENCE` if an existing SQLite production state
must be migrated; otherwise record `NOT APPLICABLE — fresh PostgreSQL` with an
owner and change record.

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
- GitHub server-side ruleset state, required checks, CodeQL, Dependency Review,
  Dependabot, secret scanning, package retention, and release access;
- trusted Windows MSIX signing secrets if Windows packages are part of the
  production release.

Record the environment identifier, image digest, database snapshot identifier,
configuration revision, owners, RPO/RTO, and incident contacts together.

**Status:** `PENDING EXTERNAL EVIDENCE`.

### Stage 3: Run failure and recovery drills

Run each applicable drill against staging and attach command output or dashboard evidence:

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
   authenticated smoke test; exercise managed PITR when the platform supports
   it and record RPO/RTO.
8. Redeploy the previous immutable image and verify schema/data compatibility;
   do not restore data solely to roll back a compatible application image.
9. Verify release automation behavior with the configured Windows signing
   posture without exposing signing material.

**Status:** `PENDING EXTERNAL EVIDENCE`.

### Stage 4: Controlled rollout

Promote only after hardening tests, staging drills, release artifact checks,
backup/restore evidence, identity/network review, GitHub operations review, and
owner sign-offs are attached to the change record. Start with a bounded
tenant/traffic cohort, monitor queue age, lease recovery, provider health,
outbox pending count, failure/dead-letter rate, and audit-chain errors, then
expand on explicit rollback criteria.

**Status:** blocked until Stage 1–3 mandatory evidence is complete and a GO
decision is recorded.

### Stage 5: Recurring operations

Track credential rotation, backup restore cadence, dependency updates, image
releases, GHCR package cleanup, GitHub alert triage, ruleset changes, alert
ownership, cost budgets, RPO/RTO results, and incident actions. Re-audit the
at-least-once boundaries whenever a provider, mutating tool, scheduler target,
or external outbox consumer changes.

## Validation matrix

### Repository-local / CI

```bash
python -m compileall -q zworkforce tests scripts
PYTHONPATH=. python -m unittest discover -s tests -v
python scripts/verify_release.py --expected 3.0.3
bash -n setup.sh scripts/*.sh packages/zarvis/scripts/*.sh packages/zarvis/scripts/git-gpg/*.sh packages/zarvis/services/voice-agent/entrypoint.sh
pnpm --dir packages/zarvis install --frozen-lockfile
pnpm --dir packages/zarvis peers check
pnpm --dir packages/zarvis test
pnpm --dir packages/zarvis audit --audit-level high
ZWORKFORCE_TEST_POSTGRES_URL="${ZWORKFORCE_TEST_POSTGRES_URL:?set a real PostgreSQL URL}" PYTHONPATH=. python -m unittest tests.test_v3_postgres -v
docker build --build-arg VERSION=3.0.3 -t zworkforce:3.0.3 .
```

The external PostgreSQL command requires a real service. A skipped PostgreSQL
suite is not PostgreSQL evidence. Docker and package commands require the
corresponding runtimes.

### Remote and operator-owned

- Confirm the exact candidate SHA has all globally required checks green and
  all affected path-filtered checks green.
- Reconcile `.github/rulesets/main.json` with the actual default-branch GitHub
  Ruleset and record its URL/ID.
- Confirm the intended release tag is signed/immutable, created only after GO,
  and points to a commit reachable from protected `main`.
- Confirm artifact checksums, SBOM, provenance, package contents, and image
  digest through GitHub.
- Capture staging doctor output, authenticated smoke output, migration posture,
  backup/restore/PITR output, failure-drill results, alert routing, Windows
  package evidence where applicable, and sign-offs.

## Completion criteria

**Repository candidate readiness** is complete when:

- the version contract is internally consistent at `3.0.3`;
- full tests, release verification, package audits, shell syntax checks, and
  GitHub Actions are green for the exact candidate SHA;
- documentation links and repository/ruleset policy tests pass;
- production examples cannot start with mock providers;
- scheduler/workflow/outbox/tenant-isolation/secret/release regressions remain
  covered; and
- the candidate PR is reviewed with no unresolved release-blocking finding.

**Production readiness** is complete only after the operator stages provide
real evidence for the exact immutable image, PostgreSQL state, configuration
revision, identity/network controls, recovery drills, server-side GitHub
controls, package retention, RPO/RTO, owners, and rollback path. Do not mark
production readiness complete from repository CI alone.
