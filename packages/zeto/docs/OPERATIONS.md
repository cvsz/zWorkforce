# Operations Runbook

## Startup

Provide `POSTGRES_PASSWORD`, `SECRET_ENCRYPTION_KEY`, `ADMIN_INITIAL_PASSWORD`, and `METRICS_TOKEN` through the deployment secret manager, then run:

```bash
docker compose up -d --build
curl --fail http://127.0.0.1:5000/ready
```

`/health` is the process liveness check. `/ready` verifies migrations have completed and PostgreSQL accepts queries. Remove `ADMIN_INITIAL_PASSWORD` from the runtime secret set after the initial administrator is persisted and a replacement credential has been verified.

## Backup

Create backups on encrypted, access-controlled storage. The repository command produces a mode-600 PostgreSQL custom archive and SHA-256 checksum:

```bash
DATABASE_URL=postgres://... BACKUP_DIR=/secure/zeto npm run db:backup
```

Back up configured object storage in the same recovery point. Never place dumps in the repository.

## Restore Verification

Restore only into a disposable isolated database before declaring the backup usable:

```bash
DATABASE_URL=postgres://... \
RESTORE_DATABASE_URL=postgres://.../zeto_restore_test \
npm run db:verify-backup -- /secure/zeto/zeto-YYYYMMDDTHHMMSSZ.dump
```

A backup is not verified until this restore exercise succeeds. Record timestamp, archive checksum, database version, migration versions, object-store snapshot, operator, and result.

## Metrics

Scrape `GET /metrics` with `Authorization: Bearer $METRICS_TOKEN`. Alert on readiness failure, HTTP 5xx rate, failed jobs/publications, stuck workflow heartbeats, and sustained queue growth. Keep this token separate from user sessions and provider credentials.

## Load Baseline

Run `npm run load:baseline` against the local production stack before release. Defaults are 20 concurrent clients for 10 seconds, zero tolerated errors, and a 500 ms p95 ceiling. Override `LOAD_URL`, `LOAD_DURATION_MS`, `LOAD_CONCURRENCY`, or `LOAD_MAX_P95_MS` for the target environment and retain the JSON result with the release evidence.

## Incident Response

1. Set the deployment kill switch or stop the app service to halt autonomous publishing.
2. Preserve logs, audit records, workflow IDs, provider response metadata, and affected publication IDs.
3. Revoke compromised provider credentials and session tokens.
4. Assess duplicate-publication and approval-bypass exposure before resuming workers.
5. Restore service gradually, monitor queue depth/error rate, and document the timeline and corrective actions.

## Rollback

Application rollback uses the previous immutable image. Database migrations are forward-safe and are not automatically reversed; restore the verified pre-deployment backup only when forward repair is unsafe. Never run destructive rollback against the only production copy.
