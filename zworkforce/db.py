from __future__ import annotations

from .db_base import DatabaseBase, SCHEMA_VERSION, TERMINAL_STATUSES, json_dumps, json_loads, utc_after, utcnow
from .db_migration import MigrationMixin
from .db_tasks import TaskMixin
from .db_finops import FinOpsMixin
from .db_governance import GovernanceMixin
from .db_automation import AutomationMixin


class Database(AutomationMixin, TaskMixin, FinOpsMixin, GovernanceMixin, MigrationMixin, DatabaseBase):
    def ready(self) -> bool:
        try:
            with self.connection() as c:
                row = c.execute("SELECT 1").fetchone()
                return bool(row and row[0] == 1)
        except Exception:
            return False

    def claim_next_task(self, worker_id: str, lease_seconds: int):
        if self.backend_kind != "postgres":
            return super().claim_next_task(worker_id, lease_seconds)
        return self._claim_next_task_postgres(worker_id, lease_seconds)

    def _claim_next_task_postgres(self, worker_id: str, lease_seconds: int):
        now = utcnow()
        lease_until = utc_after(lease_seconds)
        with self.connection() as c:
            c.execute("BEGIN")
            try:
                row = c.execute(
                    """SELECT * FROM tasks2 WHERE status='queued' AND cancel_requested=0 AND run_after<=?
                    ORDER BY priority DESC,created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED""",
                    (now,),
                ).fetchone()
                if not row:
                    c.execute("COMMIT")
                    return None
                task_id = row["id"]
                next_attempt = int(row["attempt"]) + 1
                if next_attempt > int(row["max_attempts"]):
                    c.execute(
                        "UPDATE tasks2 SET status='dead_letter',error='max attempts exhausted',finished_at=?,updated_at=? WHERE id=?",
                        (now, now, task_id),
                    )
                    c.execute("COMMIT")
                    return None
                c.execute(
                    """UPDATE tasks2 SET status='running',attempt=?,lease_owner=?,lease_expires_at=?,heartbeat_at=?,
                    started_at=COALESCE(started_at,?),updated_at=? WHERE id=?""",
                    (next_attempt, worker_id, lease_until, now, now, now, task_id),
                )
                claimed = c.execute("SELECT * FROM tasks2 WHERE id=?", (task_id,)).fetchone()
                c.execute("COMMIT")
            except Exception:
                c.execute("ROLLBACK")
                raise
        task = self._decode(dict(claimed))
        self.task_event(task["tenant_id"], task_id, "claimed", worker_id,
                        {"attempt": next_attempt, "lease_expires_at": lease_until, "backend": "postgres"})
        return task


__all__ = ["Database", "SCHEMA_VERSION", "TERMINAL_STATUSES", "json_dumps", "json_loads", "utc_after", "utcnow"]
