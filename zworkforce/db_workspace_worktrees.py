from __future__ import annotations

import uuid
from typing import Any

from .db_base import utcnow

_WORKTREE_STATUSES = {"active", "removing", "removed", "error"}


class WorkspaceWorktreeMixin:
    def create_workspace_worktree_record(
        self,
        tenant_id: str,
        grant_id: str,
        actor: str,
        *,
        repo_relative: str,
        worktree_relative: str,
        branch: str,
        start_ref: str,
        expires_at: str,
        task_id: str | None = None,
        worktree_id: str | None = None,
    ) -> dict[str, Any]:
        self.ensure_tenant(tenant_id)
        worktree_id = str(worktree_id or uuid.uuid4())
        try:
            uuid.UUID(worktree_id)
        except ValueError as exc:
            raise ValueError("workspace worktree id must be a UUID") from exc
        grant = self.get_workspace_grant(tenant_id, grant_id)
        if not grant:
            raise ValueError("workspace grant not found")
        repo_relative = str(repo_relative or "").strip()
        worktree_relative = str(worktree_relative or "").strip()
        branch = str(branch or "").strip()
        start_ref = str(start_ref or "HEAD").strip()
        task_id = str(task_id).strip() if task_id else None
        if not repo_relative or len(repo_relative) > 1024:
            raise ValueError("repo_relative is required and must be <= 1024 characters")
        if not worktree_relative or len(worktree_relative) > 1024:
            raise ValueError("worktree_relative is required and must be <= 1024 characters")
        if not branch or len(branch) > 128:
            raise ValueError("branch is required and must be <= 128 characters")
        if not start_ref or len(start_ref) > 256:
            raise ValueError("start_ref is required and must be <= 256 characters")
        if task_id and len(task_id) > 128:
            raise ValueError("task_id must be <= 128 characters")
        if task_id and hasattr(self, "get_task") and not self.get_task(tenant_id, task_id):
            raise ValueError("task not found")
        if len(str(expires_at or "")) > 64 or not str(expires_at or "").strip():
            raise ValueError("expires_at is required")
        with self.connection() as c:
            duplicate = c.execute(
                """SELECT id FROM workspace_worktrees7
                WHERE tenant_id=? AND grant_id=? AND worktree_relative=?
                  AND status IN ('active','removing') LIMIT 1""",
                (tenant_id, grant_id, worktree_relative),
            ).fetchone()
            if duplicate:
                raise ValueError("an active workspace worktree already owns this path")
            now = utcnow()
            c.execute(
                """INSERT INTO workspace_worktrees7(
                    tenant_id,id,grant_id,repo_relative,worktree_relative,branch,start_ref,status,
                    task_id,created_by,expires_at,last_error,created_at,updated_at,removed_at
                ) VALUES(?,?,?,?,?,?,?,'active',?,?,?,'',?,?,NULL)""",
                (
                    tenant_id,
                    worktree_id,
                    grant_id,
                    repo_relative,
                    worktree_relative,
                    branch,
                    start_ref,
                    task_id,
                    actor,
                    str(expires_at).strip(),
                    now,
                    now,
                ),
            )
        result = self.get_workspace_worktree_record(tenant_id, worktree_id)
        if not result:
            raise RuntimeError("workspace worktree record could not be stored")
        return result

    def get_workspace_worktree_record(self, tenant_id: str, worktree_id: str) -> dict[str, Any] | None:
        with self.connection() as c:
            row = c.execute(
                "SELECT * FROM workspace_worktrees7 WHERE tenant_id=? AND id=?",
                (tenant_id, worktree_id),
            ).fetchone()
        return dict(row) if row else None

    def get_active_workspace_worktree_by_path(
        self, tenant_id: str, grant_id: str, worktree_relative: str
    ) -> dict[str, Any] | None:
        with self.connection() as c:
            row = c.execute(
                """SELECT * FROM workspace_worktrees7
                WHERE tenant_id=? AND grant_id=? AND worktree_relative=?
                  AND status IN ('active','removing')
                ORDER BY created_at DESC,id DESC LIMIT 1""",
                (tenant_id, grant_id, worktree_relative),
            ).fetchone()
        return dict(row) if row else None

    def list_workspace_worktrees(
        self,
        tenant_id: str,
        *,
        status: str | None = None,
        grant_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses = ["tenant_id=?"]
        args: list[Any] = [tenant_id]
        if status is not None:
            if status not in _WORKTREE_STATUSES:
                raise ValueError("invalid workspace worktree status")
            clauses.append("status=?")
            args.append(status)
        if grant_id:
            clauses.append("grant_id=?")
            args.append(grant_id)
        args.extend((max(1, min(int(limit), 500)), max(0, int(offset))))
        with self.connection() as c:
            rows = c.execute(
                "SELECT * FROM workspace_worktrees7 WHERE "
                + " AND ".join(clauses)
                + " ORDER BY updated_at DESC,id ASC LIMIT ? OFFSET ?",
                tuple(args),
            ).fetchall()
        return self._rows(rows)

    def set_workspace_worktree_status(
        self,
        tenant_id: str,
        worktree_id: str,
        status: str,
        *,
        error: str = "",
    ) -> dict[str, Any]:
        if status not in _WORKTREE_STATUSES:
            raise ValueError("invalid workspace worktree status")
        current = self.get_workspace_worktree_record(tenant_id, worktree_id)
        if not current:
            raise ValueError("workspace worktree not found")
        now = utcnow()
        removed_at = now if status == "removed" else current.get("removed_at")
        with self.connection() as c:
            c.execute(
                """UPDATE workspace_worktrees7
                SET status=?,last_error=?,updated_at=?,removed_at=?
                WHERE tenant_id=? AND id=?""",
                (status, str(error or "")[:1000], now, removed_at, tenant_id, worktree_id),
            )
        return self.get_workspace_worktree_record(tenant_id, worktree_id) or {}

    def list_expired_workspace_worktrees(self, tenant_id: str, now: str, *, limit: int = 100) -> list[dict[str, Any]]:
        with self.connection() as c:
            rows = c.execute(
                """SELECT * FROM workspace_worktrees7
                WHERE tenant_id=? AND status='active' AND expires_at<=?
                ORDER BY expires_at ASC,id ASC LIMIT ?""",
                (tenant_id, now, max(1, min(int(limit), 500))),
            ).fetchall()
        return self._rows(rows)
