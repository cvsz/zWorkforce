# PostgreSQL distributed runtime

Set:

```env
ZWORKFORCE_DATABASE_URL=postgresql://user:password@host:5432/zworkforce
```

The repository automatically selects PostgreSQL based on URI scheme. psycopg executes parameterized statements through a compatibility layer so the same repository mixins serve SQLite and PostgreSQL.

## Queue semantics

PostgreSQL workers claim with:

```sql
SELECT *
FROM tasks2
WHERE status='queued'
  AND cancel_requested=0
  AND run_after<=now_value
ORDER BY priority DESC, created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;
```

The selected row is transitioned to `running`, attempt count increments and a lease owner/expiry/heartbeat is recorded before commit.

## Production recommendations

- Require TLS for non-local DB connections.
- Use managed HA or equivalent streaming-replication/failover architecture.
- Enable automated backups and PITR.
- Monitor storage growth in tasks, events, audit and usage ledgers.
- Use connection pooling/proxying when API/worker counts become large; v3 opens short-lived repository connections by design.
- Keep application and database clocks synchronized.

## Migration

SQLite remains supported. v3 does not automatically copy SQLite contents into PostgreSQL. For production migration, freeze writes, export tenant data through a controlled migration process, verify counts/audit chains, then switch `ZWORKFORCE_DATABASE_URL`.
