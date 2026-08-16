from __future__ import annotations

from typing import Any


class EvidenceMixin:
    """Bounded read-only projections over existing durable execution tables."""

    def list_child_tasks(self, tenant_id: str, parent_task_id: str, limit: int = 100) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), 500))
        with self.connection() as c:
            rows = c.execute(
                "SELECT * FROM tasks2 WHERE tenant_id=? AND parent_task_id=? ORDER BY created_at,id LIMIT ?",
                (tenant_id, parent_task_id, bounded),
            ).fetchall()
            return self._rows(rows)

    def list_task_artifacts(self, tenant_id: str, task_id: str, limit: int = 100) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), 500))
        with self.connection() as c:
            rows = c.execute(
                "SELECT * FROM artifacts3 WHERE tenant_id=? AND task_id=? ORDER BY created_at,id LIMIT ?",
                (tenant_id, task_id, bounded),
            ).fetchall()
            return self._rows(rows)

    def list_workflow_refs_for_task(self, tenant_id: str, task_id: str, limit: int = 50) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), 200))
        with self.connection() as c:
            rows = c.execute(
                """SELECT s.run_id,s.step_id,s.agent_id,s.status,s.depends_on_json,s.started_at,s.finished_at,
                r.workflow_id,r.workflow_version,r.status AS workflow_status,r.actor AS workflow_actor,
                r.created_at AS workflow_created_at,r.finished_at AS workflow_finished_at
                FROM workflow_steps3 s
                JOIN workflow_runs3 r ON r.id=s.run_id AND r.tenant_id=s.tenant_id
                WHERE s.tenant_id=? AND s.task_id=?
                ORDER BY r.created_at,s.step_id LIMIT ?""",
                (tenant_id, task_id, bounded),
            ).fetchall()
            return self._rows(rows)
