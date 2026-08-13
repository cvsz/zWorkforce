---
name: zworkforce-postgres-recovery
description: Verify zWorkforce PostgreSQL operations including schema migrations, advisory-lock initialization, backups, restores, disaster-recovery drills, queue recovery, outbox recovery, and migration rollback evidence.
---

# zWorkforce PostgreSQL Recovery

Treat database operations as production-impacting even in dry runs.

## Workflow

1. Identify backend mode, schema version, tenant scope, and affected tables.
2. Verify backups before migrations or destructive maintenance.
3. Check advisory-lock initialization, transactional rollback, leases, queue
   claims, scheduler/outbox leadership, and dead-letter recovery.
4. Run restore drills against an isolated target before claiming recoverability.
5. Capture command output, timestamps, data counts, and rollback decision.

## References

- `docs/POSTGRESQL.md`
- `docs/DISASTER-RECOVERY.md`
- `zworkforce/db_schema_v3.py`
- `zworkforce/db_backend.py`
- `tests/test_v3_postgres.py`
- `tests/test_postgres_initialization.py`

## Output

Report backup status, restore status, schema compatibility, data validation,
remaining RPO/RTO risk, and operator actions.
