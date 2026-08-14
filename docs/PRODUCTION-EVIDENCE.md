# Production Release Evidence — zWorkforce v3.0.3

This ledger is the evidence boundary between repository-complete release readiness and environment-complete production readiness.

**Rule:** an item remains `PENDING EXTERNAL EVIDENCE` until an operator records the real environment, timestamp, command or run URL, result, and durable artifact/reference. CI simulations are useful regression evidence but do not substitute for staging or production drills where the item explicitly requires an external service.

## Candidate identity

| Field | Value |
| --- | --- |
| Candidate version | `3.0.3` |
| Candidate branch | `agent/exec-plan-v3.0.3-readiness` |
| Commit SHA | _record after final candidate commit_ |
| Release tag | _create only after merge and all mandatory evidence_ |
| OCI image digest | _record immutable GHCR digest after publication_ |
| Python artifact checksums | _record from release workflow_ |

## Repository gates

| Gate | Required evidence | Status |
| --- | --- | --- |
| Python 3.12 / 3.13 / 3.14 | GitHub check URLs for `test (3.12)`, `test (3.13)`, `test (3.14)` | PENDING CI |
| PostgreSQL integration | `postgres-integration` check URL | PENDING CI |
| Documentation / ruleset contract | `documentation-contract` check URL | PENDING CI |
| Release integrity | `release-integrity` check URL | PENDING CI |
| Container build | `container` check URL | PENDING CI |
| Security invariants | `security-invariants` check URL | PENDING CI |
| Dependency review | `dependency-review` check URL | PENDING CI |
| CodeQL | `Analyze (python)`, `Analyze (actions)`, and PR `CodeQL` result | PENDING CI |
| Windows client | `build-test-package` check URL and MSIX artifact name | PENDING CI |

## Stage A — staging topology and secrets

Status: **PENDING EXTERNAL EVIDENCE**

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

Status: **PENDING EXTERNAL EVIDENCE**

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

Status: **PENDING EXTERNAL EVIDENCE**

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

Status: **PENDING EXTERNAL EVIDENCE**

Verify with configured external providers:
- Luna/Terra/Sol routing resolves to intended models;
- primary provider failure opens the expected circuit/fallback path;
- retry and timeout budgets remain bounded;
- mutating tools remain deny-by-default unless explicit grant/approval exists;
- provider credentials remain server-side.

```text
Provider set:
Failure injected:
Fallback observed:
Circuit/metric evidence:
Bounded timeout/retry evidence:
Result:
Artifact/reference:
```

## Stage E — scheduler, worker, outbox, and HA leases

Status: **PENDING EXTERNAL EVIDENCE**

With at least two eligible replicas where the deployment topology supports it:
- prove only one scheduler lease holder performs each due action;
- prove only one outbox lease holder dispatches each event;
- terminate the current leader and record failover time;
- verify task lease expiry/reclaim after worker interruption;
- verify webhook dedupe, HMAC signature, retry/backoff, and dead-letter behavior.

```text
Replica counts:
Leader before failure:
Failure time (UTC):
New leader time (UTC):
Observed failover:
Duplicate count:
Dead-letter/retry evidence:
Result:
Artifact/reference:
```

## Stage F — artifacts, memory, and external storage

Status: **PENDING EXTERNAL EVIDENCE**

When enabled in the target environment:
- store and retrieve an S3-compatible content-addressed artifact and verify SHA-256;
- search/reindex Qdrant-backed semantic memory;
- rotate storage credentials/references without exposing secrets;
- verify tenant isolation for artifact and memory access.

```text
Artifact backend:
Vector backend:
Artifact SHA-256:
Cross-tenant negative test:
Result:
Artifact/reference:
```

## Stage G — observability and SLO evidence

Status: **PENDING EXTERNAL EVIDENCE**

Verify:
- `/health`, `/ready`, and authenticated `/metrics` from the deployed environment;
- OTLP trace reaches the configured collector/backend;
- queue depth, dead-letter, provider health, cost, outcome, and SLO metrics are visible;
- one intentional failure can be correlated by request/task/trace identifiers;
- alert routing reaches the intended operator channel.

```text
Metrics backend:
Trace backend:
Trace/request/task IDs:
Alert test:
Result:
Dashboard/run URL:
```

## Stage H — Windows operator client

Status: **PENDING EXTERNAL EVIDENCE**

Verify the signed/approved Windows package against the deployed HTTPS endpoint:
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
- all required GitHub checks are green on the exact candidate SHA;
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

A `GO` decision authorizes merging the candidate, creating immutable tag `v3.0.3`, running the tag-driven release workflow, and recording release artifact checksums and GHCR digest back into this ledger or the release record.
