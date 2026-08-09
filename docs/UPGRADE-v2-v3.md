# Upgrade v2 -> v3

## Compatibility
- Existing SQLite v2 tables remain valid.
- v3 initializes additional `*3` tables without deleting v2 task/agent/audit state.
- Existing `/api/v1` core endpoints remain supported.
- Existing provider/tool/approval behavior remains unless a tenant policy explicitly denies an action.

## Steps

1. Back up the database and workspace.
2. Deploy v3 code with SQLite first if you want an in-place application upgrade.
3. Run `zworkforce doctor` and `zworkforce audit-verify`.
4. Configure workflows/schedules/policies/evaluations as needed.
5. If moving to PostgreSQL, perform a controlled data migration and verify counts/audit chains before switching traffic; v3 does not silently copy SQLite into PostgreSQL.
6. Configure OIDC, OTLP, S3/Qdrant and secret references only after their external services are ready.
7. Run the supplied CI/test matrix and production smoke tests.

## Breaking operational change
Production Compose v3 uses PostgreSQL by default and therefore requires `ZWORKFORCE_POSTGRES_PASSWORD` plus production API credentials.
