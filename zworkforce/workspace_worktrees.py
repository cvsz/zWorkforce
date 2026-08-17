from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .workspace_grants import WorkspaceGrantService
from .worktree import (
    GitWorktreeAdapter,
    WorktreeCommandResult,
    WorktreeCommitResult,
    WorktreeError,
    WorktreeStatus,
)


MutationAuthorizer = Callable[[str, str, str, str], None]


class WorkspaceWorktreeService:
    """Control-plane binding for tenant-scoped, grant-bounded Git worktrees.

    Mutations require the existing policy/approval authorizer. Durable lifecycle
    rows make ownership, expiry and cleanup reviewable without inventing a new
    control plane.
    """

    def __init__(
        self,
        settings,
        db,
        *,
        mutation_authorizer: MutationAuthorizer | None = None,
        adapter_factory: Callable[..., GitWorktreeAdapter] = GitWorktreeAdapter,
    ):
        self.settings = settings
        self.db = db
        self.grants = WorkspaceGrantService(settings, db)
        self.mutation_authorizer = mutation_authorizer
        self.adapter_factory = adapter_factory

    def _resolved_adapter(
        self, tenant_id: str, grant_id: str, *, write: bool = False
    ) -> tuple[dict[str, Any], GitWorktreeAdapter]:
        grant, root = self.grants.resolve_root(
            tenant_id,
            grant_id,
            require_read=True,
            require_write=write,
        )
        return grant, self.adapter_factory(
            grant_root=root,
            grant_write=bool(grant.get("write")),
            grant_commands=tuple(grant.get("commands") or ()),
        )

    def _adapter(self, tenant_id: str, grant_id: str, *, write: bool = False) -> GitWorktreeAdapter:
        return self._resolved_adapter(tenant_id, grant_id, write=write)[1]

    def _cleanup_adapter(self, tenant_id: str, grant_id: str) -> GitWorktreeAdapter:
        """Build a removal-only adapter even after grant expiry/disable.

        Cleanup still requires the mutation authorizer and a durable row. The
        original canonical root, write authority and git command authority are
        revalidated; expiry/enablement are intentionally not treated as a reason
        to leave an orphaned worktree behind.
        """
        grant = self.db.get_workspace_grant(tenant_id, grant_id)
        if not grant or not grant.get("write") or "git" not in (grant.get("commands") or ()):
            raise WorktreeError("tracked worktree grant no longer permits safe cleanup")
        relative = str(grant.get("root_rel") or "")
        root_rel = self.grants.normalize_root(relative)
        if root_rel != relative:
            raise WorktreeError("workspace grant root no longer resolves to its approved canonical path")
        root = self.grants.host_root if relative == "." else (self.grants.host_root / Path(relative)).resolve(strict=True)
        return self.adapter_factory(
            grant_root=root,
            grant_write=True,
            grant_commands=tuple(grant.get("commands") or ()),
        )

    def _authorize_mutation(self, tenant_id: str, actor: str, action: str, grant_id: str) -> None:
        if self.mutation_authorizer is None:
            raise WorktreeError("worktree mutation requires the configured approval/policy authorizer")
        self.mutation_authorizer(tenant_id, actor, action, grant_id)

    def _audit(
        self,
        tenant_id: str,
        actor: str,
        action: str,
        grant_id: str,
        *,
        success: bool,
        details: Mapping[str, Any] | None = None,
        error: str = "",
    ) -> None:
        payload = {"grant_id": grant_id, "success": bool(success), **dict(details or {})}
        if error:
            payload["error"] = str(error)[:500]
        self.db.audit(tenant_id, actor, action, "workspace_grant", grant_id, payload)

    def status(self, tenant_id: str, actor: str, grant_id: str, repo_relative: str) -> WorktreeStatus:
        adapter = self._adapter(tenant_id, grant_id)
        try:
            result = adapter.status(repo_relative)
        except Exception as exc:
            self._audit(tenant_id, actor, "workspace.worktree.status", grant_id, success=False,
                        details={"repo_relative": repo_relative}, error=str(exc))
            raise
        self._audit(tenant_id, actor, "workspace.worktree.status", grant_id, success=True,
                    details={"repo_relative": repo_relative, "branch": result.branch, "dirty": result.dirty})
        return result

    def diff(self, tenant_id: str, actor: str, grant_id: str, repo_relative: str) -> str:
        adapter = self._adapter(tenant_id, grant_id)
        try:
            result = adapter.diff(repo_relative)
        except Exception as exc:
            self._audit(tenant_id, actor, "workspace.worktree.diff", grant_id, success=False,
                        details={"repo_relative": repo_relative}, error=str(exc))
            raise
        self._audit(tenant_id, actor, "workspace.worktree.diff", grant_id, success=True,
                    details={"repo_relative": repo_relative, "output_bytes": len(result.encode("utf-8"))})
        return result

    def create_feature_worktree(
        self,
        tenant_id: str,
        actor: str,
        grant_id: str,
        *,
        repo_relative: str,
        destination_relative: str,
        branch: str,
        start_ref: str = "HEAD",
        task_id: str | None = None,
    ) -> WorktreeStatus:
        self._authorize_mutation(tenant_id, actor, "workspace.worktree.create", grant_id)
        grant, adapter = self._resolved_adapter(tenant_id, grant_id, write=True)
        details = {
            "repo_relative": repo_relative,
            "destination_relative": destination_relative,
            "branch": branch,
            "start_ref": start_ref,
            "task_id": task_id or "",
        }
        created = False
        try:
            result = adapter.create_feature_worktree(
                repo_relative=repo_relative,
                destination_relative=destination_relative,
                branch=branch,
                start_ref=start_ref,
            )
            created = True
            record = self.db.create_workspace_worktree_record(
                tenant_id,
                grant_id,
                actor,
                repo_relative=repo_relative,
                worktree_relative=destination_relative,
                branch=branch,
                start_ref=start_ref,
                expires_at=str(grant["expires_at"]),
                task_id=task_id,
            )
            details["worktree_id"] = record["id"]
        except Exception as exc:
            if created:
                try:
                    adapter.remove_worktree(repo_relative=repo_relative, worktree_relative=destination_relative)
                except Exception as cleanup_exc:
                    exc = WorktreeError(f"worktree lifecycle persistence failed and rollback cleanup failed: {cleanup_exc}")
            self._audit(tenant_id, actor, "workspace.worktree.create", grant_id, success=False, details=details, error=str(exc))
            raise exc
        self._audit(tenant_id, actor, "workspace.worktree.create", grant_id, success=True, details=details)
        return result

    def run_check(
        self,
        tenant_id: str,
        actor: str,
        grant_id: str,
        repo_relative: str,
        *,
        name: str,
        argv: Sequence[str],
        allowlisted_checks: Mapping[str, Sequence[str]],
    ) -> WorktreeCommandResult:
        adapter = self._adapter(tenant_id, grant_id)
        details = {"repo_relative": repo_relative, "check": name, "argv0": str(argv[0]) if argv else ""}
        try:
            result = adapter.run_check(repo_relative, name=name, argv=argv, allowlisted_checks=allowlisted_checks)
        except Exception as exc:
            self._audit(tenant_id, actor, "workspace.worktree.check", grant_id, success=False, details=details, error=str(exc))
            raise
        self._audit(tenant_id, actor, "workspace.worktree.check", grant_id,
                    success=result.exit_code == 0, details={**details, "exit_code": result.exit_code})
        return result

    def commit_worktree(
        self,
        tenant_id: str,
        actor: str,
        grant_id: str,
        *,
        repo_relative: str,
        worktree_relative: str,
        message: str,
    ) -> WorktreeCommitResult:
        self._authorize_mutation(tenant_id, actor, "workspace.worktree.commit", grant_id)
        record = self.db.get_active_workspace_worktree_by_path(tenant_id, grant_id, worktree_relative)
        if not record:
            raise WorktreeError("worktree is not tracked as an active tenant lifecycle record")
        if str(record["repo_relative"]) != str(repo_relative):
            raise WorktreeError("tracked worktree repository does not match commit request")
        adapter = self._adapter(tenant_id, grant_id, write=True)
        details = {
            "repo_relative": repo_relative,
            "worktree_relative": worktree_relative,
            "worktree_id": record["id"],
            "branch": record["branch"],
        }
        try:
            result = adapter.commit(
                worktree_relative,
                message=message,
                expected_branch=str(record["branch"]),
            )
        except Exception as exc:
            self._audit(tenant_id, actor, "workspace.worktree.commit", grant_id, success=False, details=details, error=str(exc))
            raise
        self._audit(
            tenant_id,
            actor,
            "workspace.worktree.commit",
            grant_id,
            success=True,
            details={**details, "commit_sha": result.commit_sha},
        )
        return result

    def remove_worktree(
        self,
        tenant_id: str,
        actor: str,
        grant_id: str,
        *,
        repo_relative: str,
        worktree_relative: str,
        allow_expired_grant_cleanup: bool = False,
    ) -> None:
        self._authorize_mutation(tenant_id, actor, "workspace.worktree.remove", grant_id)
        record = self.db.get_active_workspace_worktree_by_path(tenant_id, grant_id, worktree_relative)
        if not record:
            raise WorktreeError("worktree is not tracked as an active tenant lifecycle record")
        if str(record["repo_relative"]) != str(repo_relative):
            raise WorktreeError("tracked worktree repository does not match removal request")
        adapter = self._cleanup_adapter(tenant_id, grant_id) if allow_expired_grant_cleanup else self._adapter(
            tenant_id, grant_id, write=True
        )
        details = {
            "repo_relative": repo_relative,
            "worktree_relative": worktree_relative,
            "worktree_id": record["id"],
        }
        self.db.set_workspace_worktree_status(tenant_id, record["id"], "removing")
        try:
            adapter.remove_worktree(repo_relative=repo_relative, worktree_relative=worktree_relative)
        except Exception as exc:
            self.db.set_workspace_worktree_status(tenant_id, record["id"], "active", error=str(exc))
            self._audit(tenant_id, actor, "workspace.worktree.remove", grant_id, success=False, details=details, error=str(exc))
            raise
        self.db.set_workspace_worktree_status(tenant_id, record["id"], "removed")
        self._audit(tenant_id, actor, "workspace.worktree.remove", grant_id, success=True, details=details)

    def cleanup_expired(self, tenant_id: str, actor: str, *, limit: int = 100) -> dict[str, int]:
        """Remove expired tracked worktrees under explicit mutation authorization."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        rows = self.db.list_expired_workspace_worktrees(tenant_id, now, limit=limit)
        removed = 0
        failed = 0
        for row in rows:
            try:
                self.remove_worktree(
                    tenant_id,
                    actor,
                    row["grant_id"],
                    repo_relative=row["repo_relative"],
                    worktree_relative=row["worktree_relative"],
                    allow_expired_grant_cleanup=True,
                )
            except Exception:
                failed += 1
            else:
                removed += 1
        return {"matched": len(rows), "removed": removed, "failed": failed}
