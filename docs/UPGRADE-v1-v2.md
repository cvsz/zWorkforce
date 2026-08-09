# Upgrade: v1.x to v2.0

v2 uses new tenant-aware tables (`agents2`, `tasks2`, `usage_events2`, etc.) to avoid destructive in-place rewrites of v1 SQLite tables.

On startup:

1. v2 schema is created idempotently;
2. the default tenant is created and seeded;
3. if legacy `agents`/`tasks` tables exist and migration has not run, v1 records are copied into the default tenant;
4. legacy running tasks are migrated as queued so they can be safely reclaimed;
5. usage, budgets, approvals and audit history are copied where present;
6. a `v1_copy_complete` marker prevents duplicate copies;
7. legacy tables remain untouched for rollback/forensics.

Before upgrading production data:

- take a consistent SQLite backup/snapshot;
- start v2 with workers disabled (`ZWORKFORCE_EMBEDDED_WORKERS=0`);
- run `zworkforce init` then `zworkforce doctor`;
- verify agent/task counts and `zworkforce audit-verify`;
- start worker processes only after validation.

v2 idempotency keys are scoped to tenant + actor and do not reuse the v1 global idempotency table.
