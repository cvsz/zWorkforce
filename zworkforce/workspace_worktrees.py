from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Mapping, Sequence

from .workspace_grants import WorkspaceGrantService
from .worktree import GitWorktreeAdapter, WorktreeCommandResult, WorktreeError, WorktreeStatus


MutationAuthorizer = Callable[[str, str, str, str], None]


class WorkspaceWorktreeService:
    """Control-plane binding for tenant-scoped, grant-bounded Git worktrees.

    This service deliberately does not invent a new approval system. Mutating
    operations require an injected authorizer owned by the existing policy /
    approval boundary. Read-only inspection can run without one.
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

    def _adapter(self, tenant_id: str, grant_id: str, *, write: bool = False) -> GitWorktreeAdapter:
        grant, root = self.grants.resolve_root(
            tenant_id,
            grant_id,
            require_read=True,
            require_write=write,
        )
        return self.adapter_factory(
            grant_root=root,
            grant_write=bool(grant.get("write")),
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
            self._audit(
                tenant_id,
                actor,
                "workspace.worktree.status",
                grant_id,
                success=False,
                details={"repo_relative": repo_relative},
                error=str(exc),
            )
            raise
        self._audit(
            tenant_id,
            actor,
            "workspace.worktree.status",
            grant_id,
            success=True,
            details={"repo_relative": repo_relative, "branch": result.branch, "dirty": result.dirty},
        )
        return result

    def diff(self, tenant_id: str, actor: str, grant_id: str, repo_relative: str) -> str:
        adapter = self._adapter(tenant_id, grant_id)
        try:
            result = adapter.diff(repo_relative)
        except Exception as exc:
            self._audit(
                tenant_id,
                actor,
                "workspace.worktree.diff",
                grant_id,
                success=False,
                details={"repo_relative": repo_relative},
                error=str(exc),
            )
            raise
        self._audit(
            tenant_id,
            actor,
            "workspace.worktree.diff",
            grant_id,
            success=True,
            details={"repo_relative": repo_relative, "output_bytes": len(result.encode("utf-8"))},
        )
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
    ) -> WorktreeStatus:
        self._authorize_mutation(tenant_id, actor, "workspace.worktree.create", grant_id)
        adapter = self._adapter(tenant_id, grant_id, write=True)
        details = {
            "repo_relative": repo_relative,
            "destination_relative": destination_relative,
            "branch": branch,
            "start_ref": start_ref,
        }
        try:
            result = adapter.create_feature_worktree(
                repo_relative=repo_relative,
                destination_relative=destination_relative,
                branch=branch,
                start_ref=start_ref,
            )
        except Exception as exc:
            self._audit(tenant_id, actor, "workspace.worktree.create", grant_id, success=False, details=details, error=str(exc))
            raise
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
        self._audit(
            tenant_id,
            actor,
            "workspace.worktree.check",
            grant_id,
            success=result.exit_code == 0,
            details={**details, "exit_code": result.exit_code},
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
    ) -> None:
        self._authorize_mutation(tenant_id, actor, "workspace.worktree.remove", grant_id)
        adapter = self._adapter(tenant_id, grant_id, write=True)
        details = {"repo_relative": repo_relative, "worktree_relative": worktree_relative}
        try:
            adapter.remove_worktree(repo_relative=repo_relative, worktree_relative=worktree_relative)
        except Exception as exc:
            self._audit(tenant_id, actor, "workspace.worktree.remove", grant_id, success=False, details=details, error=str(exc))
            raise
        self._audit(tenant_id, actor, "workspace.worktree.remove", grant_id, success=True, details=details)
