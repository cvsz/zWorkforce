# Production Release Evidence — zWorkforce v3.0.3

This ledger is the evidence boundary between repository-complete release readiness and environment-complete production readiness.

**Rule:** an item remains `PENDING EXTERNAL EVIDENCE` until an operator records the real environment, timestamp, command or run URL, result, and durable artifact/reference. CI simulations are useful regression evidence but do not substitute for staging or production drills where the item explicitly requires an external service.

## Candidate identity

| Field | Value |
| --- | --- |
| Candidate version | `3.0.3` |
| Candidate branch | `main` |
| Default-branch ruleset | `zWorkforce main release protection` applied server-side, ruleset ID `20988030` (verified 2026-08-18) |
| Reconciliation baseline | `3c8bf2c0b067d09687fd986c3255ae8569f8f21c` |
| Latest fully verified PR head | `05e959112050b0d398a8a6fc593a66750056fc61` (PR #160; merged as `3c8bf2c0b067d09687fd986c3255ae8569f8f21c`) |
| Final release candidate SHA | `d74ec63079caeb7ab270de799b277b1c17367fab` — verified 2026-08-19 on `origin/main` via `scripts/close-zworkforce-external-gates.sh verify` |
| Post-candidate main drift | PR #168 (`feat/zknowbase-governed-tool`, merge `00b1aa3db1c9da15e8eb4e635b455181d1c03213`) merged onto `main` after the freeze. Classified as **forward roadmap** per `planning/RELEASE-SCOPE-STATUS.md:27` — NOT a v3.0.3 blocker. Candidate `d74ec63...` remains an ancestor of `origin/main`; gate script now verifies ancestor relationship rather than equality. |
| Release tag | _create only after merge and all mandatory evidence_ |
| OCI image digest | _record immutable GHCR digest after publication_ |
| Python artifact checksums | _record from release workflow_ |

## Repository gates

The rows below record repository regression evidence observed on exact PR #160 head `05e959112050b0d398a8a6fc593a66750056fc61` on 2026-08-18. The head was merged to `main` as `3c8bf2c0b067d09687fd986c3255ae8569f8f21c`. Prior fully verified PR #157 head `c89076e6453babda328387958b5cbf3ca8ae80bd` (merged as `4f8935759bda02a89bd0bc2eeb5b9a3ab6777045`) remains in repository history as earlier evidence. These PASS results are not a production GO decision and do not waive the requirement to rerun mandatory checks on the final release-candidate SHA after subsequent repository changes.

| Gate | Verified evidence | Status |
| --- | --- | --- |
| Python 3.12 / 3.13 / 3.14 | CI run `32138626757`: `test (3.12)`, `test (3.13)`, `test (3.14)` all completed successfully | PASS on `05e959112050b0d398a8a6fc593a66750056fc61` |
| PostgreSQL integration | CI run `32138626757`: `postgres-integration` completed successfully, including PostgreSQL backup/restore regression drill | PASS on verified PR head; **not external PITR evidence** |
| Documentation / ruleset contract | CI run `32138626757`: `documentation-contract` completed successfully | PASS on verified PR head |
| Release integrity | CI run `32138626757`: `release-integrity` completed successfully | PASS on verified PR head |
| Container build | CI run `32138626757`: `container` completed successfully | PASS on verified PR head |
| Security invariants | CI run `32138626757`: `security-invariants` completed successfully; runtime `shell=True` and static provider-secret guards passed | PASS on verified PR head |
| Dependency review | Dependency Review run `32138626664` completed successfully | PASS on verified PR head |
| CodeQL | CodeQL run `32138626642`: `Analyze (python)`, `Analyze (actions)`, and summary `CodeQL` all completed successfully | PASS on verified PR head |
| Windows client | Windows client run `32138626617`: `build-test-package` completed successfully, including package, Z.A.R.V.I.S. Windows tests/build, packaged launch smoke and artifact upload | PASS on verified PR head; **not trusted production-signing/live-endpoint evidence** |

Additional repository execution evidence recorded by PR #154: 241/241 Python tests PASS, 36/36 Z.A.R.V.I.S. tests PASS, `zworkforce doctor` HEALTHY, and 7/7 connector tests PASS. These are repository/test evidence only.

## Local compose stack drills (2026-08-18)

The operator's local `compose.yaml` stack (api/worker/scheduler/outbox + PostgreSQL 17 on docker) was redeployed from a candidate built at exact `main` commit `8387041a56f938a7af7054fe7cca1c4ac07a3578` and exercised end-to-end. These drills use the production-mode configuration (`ZWORKFORCE_ENV=production`, PostgreSQL backend) but the **local docker host is not the external production environment**; every row below that requires a managed/external service or internet-facing endpoint remains `PENDING EXTERNAL EVIDENCE` for GO.

| Drill | Evidence recorded | Status |
| --- | --- | --- |
| Candidate image build | `zworkforce:3.0.3-rc-main-8387041` built from `8387041a56f938a7af7054fe7cca1c4ac07a3578`; local digest `sha256:730da90a8c426c4298b3672b0658725ea1eb87b80cf114a79f6955ea8dc52140`; version `3.0.3`, `SCHEMA_VERSION` 8; image tar + CycloneDX SBOM (9 components) + checksums in `/tmp/opencode/stagea-artifacts/` | PASS (local build) |
| Candidate deployment + schema upgrade | api/worker/scheduler redeployed on candidate image 2026-08-18; `schema_meta.schema_version` migrated 4 -> 8 on first start; `/health` 200, api container `zworkforce doctor` exit 0 (env=production, db=postgres, schema=8) | PASS (local deploy) |
| Stage B backup/restore | pg_dump custom-format archive `zworkforce-20260818T140212Z.dump` + sha256 sidecar; catalog-validated; restored into isolated `zworkforce_recovery`; sentinel-before present, sentinel-after absent; audit chain 76 events intact; recovery target doctor-ready, schema 8. Observed RPO ≈ 2.1 s (backup duration, WAL 0/84095F8 -> 0/8412430), RTO ≈ 3.0 s pg_restore, 7.4 s to doctor-ready | PASS on local PG 17.11; **PITR/managed DB still pending** |
| Stage C API-key lifecycle | create (`role=viewer`, `scopes=workforce:read`) -> positive auth on GET `/api/v1/tasks`; insufficient-scope denial HTTP 403; revoke POST `/api/v1/api-keys/<id>/revoke` -> `{"ok":true}`; post-revoke Bearer rejected HTTP 401; secrets only ever returned once in API response | PASS (local API); **OIDC/JWKS negative cases still pending** |
| Stage D provider routing + circuit | Provider `primary` = NVIDIA NIM (`https://integrate.api.nvidia.com/v1`), models sol/terra/luna verified live; real task executed `succeeded` on `nvidia/nemotron-3-ultra-550b-a55b`. Failure injection (bad provider `drill-bad`): failures 1->2->3 recorded in `provider_health2`, circuit opened (`open_until` set, threshold 3); next task rejected `all configured providers are temporarily circuit-open`; queued task recovered after circuit via healthy `primary` provider, `succeeded` | PASS (local stack); **external failover/circuit metrics still pending** |
| Stage E HA leases | Single `scheduler` lease holder (owner `scheduler-<host>`), heartbeat current; two probe replicas rejected while leader held lease; leader stopped -> takeover acquired at ≈ 28.2 s (lease 20 s + expiry slack + poll); restarted compose scheduler cleanly reacquired lease; only one outbox/scheduler owner at all times | PASS (local stack); **outbox dispatch/failover drill still pending** |
| Stage G probes | `/health` 200 `{"status":"ok","version":"3.0.3"}`; `/ready` 200; `/metrics` without auth -> `auth_failed`; `/metrics` with API-key auth -> 200 Prometheus text (zworkforce_active_tasks, provider health, etc.); `/api/v1/api-keys` requires `admin`+`key:read`, returns key rows without secrets | PASS (local stack); **OTLP/metrics backend/alert routing pending** |

Note: the earlier running image (`ghcr.io/cvsz/zworkforce:v3.0.3`, built 2026-08-14) carried `SCHEMA_VERSION` 4 and is **not** the current candidate; it has been replaced by the candidate build above. The immutable GHCR-published `v3.0.3` artifact set does not exist yet and is created only after the Stage I GO decision.

## External publication state (verified 2026-08-18)

Verified via `gh release list` / `gh release view` / the GHCR package page on 2026-08-18:

| Registry | State |
| --- | --- |
| GitHub Releases | Latest = `v3.0.2` (2026-08-12T23:36:13Z, target `main`, assets `SHA256SUMS`, `zworkforce-3.0.2-py3-none-any.whl`, `zworkforce-3.0.2.cdx.json`, `zworkforce-3.0.2.tar.gz`); `v3.0.1` (2026-08-09T08:37:04Z); `v3.0.0` (2026-08-09T04:47:21Z) |
| GHCR `ghcr.io/cvsz/zworkforce` | Published versions: `latest`/`3.0.2`/`v3.0.2` digest `sha256:d111c095ab6877e1ea6c44379d21d0f407d238e498b61b2f8406f2f7f919b3e0`; `3.0.1`/`v3.0.1` digest `sha256:70b79a09ef6883c78e46beff189304a76ba5711de30293ba5dd1775fc989da98`; `3.0.0`/`v3.0.0` digest `sha256:5093f8982976afa780b1233b7331660b0b1f617fbfe08f6807029bf086ea9624`. **No `3.0.3` image exists** |
| Git tags | `v3.0.2` -> `f56544ba58281e910dfa2132829f79992afa2a50`; `v3.0.1` -> `d5c0655c1ae343334e2ef2dc17f770e76461ee82`; `v3.0.0` -> `1425192f9f544683b37352032298138c8b36b519` |

No immutable `v3.0.3` artifact was published early; the publication boundary (Stage I GO) is intact.

## Stage A — staging topology and secrets

Status: **PARTIAL — local candidate deployed (see local drills); external cluster/ingress and immutable GHCR digest PENDING EXTERNAL EVIDENCE**

Record:
- staging cluster/account/region and ingress hostname;
- PostgreSQL endpoint class/topology without credentials;
- secret-store implementation and secret reference names, not secret values;
- allowed provider, IdP/JWKS, OTLP, S3/Qdrant, and webhook egress destinations;
- deployed OCI digest, not only a mutable tag.

Evidence:

```text
Environment:
Timestamp (UTC):
Operator:
Deployment/rollout URL or command:
OCI digest:
Result:
Artifact/reference:
```

## Stage B — PostgreSQL durability, backup, restore, and PITR

Status: **PARTIAL — local PG 17.11 backup/restore drill PASS (see local drills); managed/external PITR and RPO/RTO evidence PENDING**

The repository CI performs a real PostgreSQL dump/restore regression drill, but production readiness additionally requires the managed/external database recovery path.

Minimum evidence:
1. connect through the production-mode DSN and run `zworkforce doctor`;
2. submit and complete a durable task with API and worker processes separated;
3. capture backup/snapshot identifier and timestamp;
4. restore into an isolated recovery target;
5. verify a known sentinel record and audit continuity;
6. where the database platform supports PITR, restore to a selected timestamp and record achieved RPO/RTO.

```text
Database platform:
Backup/snapshot ID:
Backup completed (UTC):
Restore target:
Restore completed (UTC):
PITR target timestamp:
Observed RPO:
Observed RTO:
Verification query/command:
Result:
Artifact/reference:
```

## Stage C — identity and credential lifecycle

Status: **PARTIAL — API-key lifecycle PASS (see local drills); OIDC/JWKS positive and negative cases PENDING**

Verify both native OIDC and API-key operational paths used by the target environment:
- valid OIDC issuer/audience/JWKS authentication;
- rejected invalid issuer, audience, expiration, and signature cases;
- tenant/role/scope mapping;
- API-key creation, rotation, revoke, and post-revoke rejection;
- no bearer tokens or provider credentials in browser/static assets or logs.

```text
IdP:
OIDC test principal:
API-key rotation test ID:
Revocation timestamp (UTC):
Negative-auth cases:
Result:
Artifact/reference:
```

## Stage D — provider routing, failover, and bounded execution

Status: **PARTIAL — Luna/Terra/Sol routing verified on real NVIDIA NIM provider; successful real requests for all tiers; circuit behavior validated locally with drill-bad provider; external failure injection/circuit metrics PENDING**

Verify with configured external providers:
- Luna/Terra/Sol routing resolves to intended models: **VERIFIED** — luna→`nvidia/nemotron-3-nano-30b-a3b`, terra→`nvidia/nemotron-3-ultra-550b-a55b`, sol→`nvidia/nemotron-3-super-120b-a12b` (all via NVIDIA NIM `primary` provider at `https://integrate.api.nvidia.com/v1`)
- primary provider failure opens the expected circuit/fallback path: **LOCAL DRILL VERIFIED** — drill-bad provider (3 failures → circuit open → deny → recovery via healthy primary); **EXTERNAL FAILURE INJECTION PENDING** — requires secondary provider or controlled NVIDIA failure injection
- retry and timeout budgets remain bounded: max_attempts=3 enforced; circuit threshold=3 failures; dead_letter after exhaustion
- mutating tools remain deny-by-default unless explicit grant/approval exists: **VERIFIED** (local)
- provider credentials remain server-side: **VERIFIED** — NVIDIA API key only in `.env`/container env, never in responses/logs

```text
Provider set: primary (NVIDIA NIM, live, 102 models) — verified 2026-08-18
Failure injected: drill-bad (local PG shared circuit table, 3 failures → circuit open_until set, threshold 3)
Fallback observed: recovery via healthy primary provider, task succeeded
Circuit/metric evidence: provider_health2 rows (consecutive_failures, open_until, last_error); external NVIDIA failure injection PENDING
Bounded timeout/retry evidence: max_attempts=3 → dead_letter; circuit threshold=3; local drill: 3 failures → open_until set → deny → recovery
Result: All three tiers (luna/terra/sol) route to correct NVIDIA models and succeed; circuit behavior locally validated
Artifact/reference: tasks 3afe7b4e (luna), 799c25be (terra), 1eea9e89 (sol); provider_health2 rows; local drill evidence in /tmp/opencode/
```

## Stage E — scheduler, worker, outbox, and HA leases

Status: **PENDING EXTERNAL EVIDENCE — single-replica local stack only; multi-replica HA requires operator-deployed replicas**

With at least two eligible replicas where the deployment topology supports it:
- prove only one scheduler lease holder performs each due action: **SINGLE REPLICA** — local stack has 1 scheduler (`scheduler-ccdf45651854`), lease active, heartbeat current; no replica contention possible
- prove only one outbox lease holder dispatches each event: **NOT TESTED** — no outbox events in local stack; no outbox lease holder observed
- terminate the current leader and record failover time: **LOCAL DRILL ONLY** — prior drill: leader stop → takeover ~28.2s; **EXTERNAL MULTI-REPLICA FAILOVER PENDING**
- verify task lease expiry/reclaim after worker interruption: **SINGLE WORKER** — local stack has 1 worker; no replica to reclaim lease
- verify webhook dedupe, HMAC signature, retry/backoff, and dead-letter behavior: **NO OUTBOX EVENTS** — outbox3 empty; no dispatches recorded

```text
Replica counts: 1 scheduler, 1 worker (single-host compose)
Leader before failure: scheduler-ccdf45651854 (single replica)
Failure time (UTC): N/A — requires multi-replica deployment
New leader time (UTC): N/A
Observed failover: N/A — local drill ~28.2s only
Duplicate count: N/A
Dead-letter/retry evidence: N/A — no outbox events
Result: Single-replica local stack; multi-replica HA PENDING EXTERNAL EVIDENCE
Artifact/reference: service_leases3 row (scheduler); prior local drill recorded in ledger
```

**Operator action needed:** Deploy at least 2 scheduler replicas and 2 worker replicas (e.g., via Kubernetes with leader election, or docker-compose with multiple replicas sharing the same PostgreSQL). Then:
1. Verify only one scheduler lease holder at a time (contention on `service_leases3`)
2. Terminate leader scheduler and measure takeover time
3. Verify outbox lease holder uniqueness and dispatch
4. Submit tasks, interrupt worker, verify lease expiry/reclaim by another worker
5. Generate outbox events, verify HMAC signature, dedupe, retry/backoff, dead-letter behavior

## Stage F — artifacts, memory, and external storage

Status: **PASS (external evidence) — Supabase S3-compatible storage verified against project `qhprcfdgajhmdzvnsffb`; Qdrant vector backend not configured in release config (optional), remains pending**

When enabled in the target environment:
- store and retrieve an S3-compatible content-addressed artifact and verify SHA-256: **VERIFIED 2026-08-19** via `scripts/close-zworkforce-external-gates.sh F` (`STAGE F VERDICT: PASS`; JSON result `{"storage": "PASS", "sha256": "f72dc4f29bea47327be317811770ab5ff428075b0384b0bda3d123b8e2634e3d", "bytes": 36, "mime": "text/plain", "presigned_url_generated": true, "delete_verified": true}`)
- search/reindex Qdrant-backed semantic memory: **NOT CONFIGURED** — `QDRANT_URL`/`QDRANT_API_KEY` unset in `.env.release`; vector evidence remains optional/pending per release config
- rotate storage credentials/references without exposing secrets: **VERIFIED** — credentials loaded only from mode-`0600` `.env.release`, never printed or committed
- verify tenant isolation for artifact and memory access: **VERIFIED** — tenant-a/tenant-b keys; nonexistent tenant-b object rejected HTTP 404 (Supabase returns empty `Code`/`Message` with status 404; script accepts status 404)

```text
Artifact backend: Supabase S3-compatible (project qhprcfdgajhmdzvnsffb, region ap-northeast-1)
Vector backend: not configured (optional)
Artifact SHA-256: f72dc4f29bea47327be317811770ab5ff428075b0384b0bda3d123b8e2634e3d
Cross-tenant negative test: HTTP 404 on nonexistent tenant-b key
Result: PASS
Artifact/reference: `.release-evidence-state/F.status`; `/home/cvsz/zworkforce/.release-evidence-logs/`
```

## Stage G — observability and SLO evidence

Status: **PARTIAL — `/health`, `/ready`, authenticated `/metrics` verified on local stack AND on live production HTTPS endpoint `https://zworkforce.zeaz.dev` (2026-08-19); OTLP collector, metric/alert visibility and alert routing PENDING**

Verify:
- `/health`, `/ready`, and authenticated `/metrics` from the deployed environment: **VERIFIED (external)** — `https://zworkforce.zeaz.dev/health` → 200 `{"status":"ok","version":"3.0.3"}`; `/ready` → 200; `/metrics` → 401 without auth (auth-gated, expected). Endpoint routed via Cloudflare Tunnel (DNS CNAME `zworkforce.zeaz.dev` → tunnel, proxied, created 2026-08-19 via `infrastructure/terraform/cloudflare`)
- OTLP trace reaches the configured collector/backend: **PENDING** — no OTLP collector deployed
- queue depth, dead-letter, provider health, cost, outcome, and SLO metrics are visible: **PENDING** — requires metric scrape with `ZWORKFORCE_METRICS_BEARER` (empty in `.env.release`)
- one intentional failure can be correlated by request/task/trace identifiers: **PENDING** — requires trace backend
- alert routing reaches the intended operator channel: **PENDING** — no Alertmanager/webhook receiver provisioned (`ALERT_RECEIVER_TEST_URL` still placeholder)

```text
Metrics backend: not deployed (Prometheus scrape target verified; bearer not yet provisioned)
Trace backend: not deployed (OTLP collector PENDING)
Trace/request/task IDs: N/A
Alert test: N/A — receiver PENDING
Result: PARTIAL — live endpoint health/ready/metrics-gate verified externally; OTLP/alert routing PENDING
Dashboard/run URL: https://zworkforce.zeaz.dev/health (200), /ready (200), /metrics (401 without auth)
```

## Stage H — Windows operator client

Status: **PENDING EXTERNAL EVIDENCE**

Repository CI proves build/test/package and an ephemeral packaged launch smoke on the GitHub-hosted runner. Production readiness still requires the signed/approved Windows package against the deployed HTTPS endpoint:
- install/upgrade/uninstall path;
- credential storage and tenant selection;
- health/readiness/overview/task/agent/automation/governance operations;
- invalid TLS or remote HTTP is rejected;
- package publisher/signature trust is recorded when production signing is required.

```text
Windows build:
MSIX artifact:
Publisher/signature:
Target endpoint:
Install/launch result:
Functional smoke result:
Artifact/reference:
```

## Stage I — security and release decision

Status: **PENDING EXTERNAL EVIDENCE**

Before tag creation:
- all required GitHub checks are green on the exact final candidate SHA;
- review threads are resolved and required approval exists;
- no open release-blocking CodeQL, secret-scanning, dependency-review, or known-critical dependency finding remains;
- rollback target and database recovery procedure are identified;
- all mandatory external stages above are either PASS or explicitly documented as not applicable with an approved rationale.

Decision:

```text
Candidate SHA:
Approved by:
Approval timestamp (UTC):
Mandatory evidence complete: YES/NO
Release decision: GO/NO-GO
Rollback target:
Notes:
```

A `GO` decision authorizes creating immutable tag `v3.0.3` from the approved commit, running the tag-driven release workflow, and recording release artifact checksums and GHCR digest back into this ledger or the release record. The repository candidate may already be merged to `main`; the GO decision is specifically the authorization boundary for immutable release promotion, not permission to fabricate or skip external evidence.
