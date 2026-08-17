import json
import unittest
from datetime import datetime, timedelta, timezone

from tests.common import stack
from zworkforce.workspace_grants import WorkspaceGrantService
from zworkforce.workspace_worktrees import WorkspaceWorktreeService
from zworkforce.worktree import WorktreeCommandResult, WorktreeCommitResult, WorktreeError, WorktreeStatus


class FakeAdapter:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []
        FakeAdapter.instances.append(self)

    def status(self, repo_relative):
        self.calls.append(("status", repo_relative))
        return WorktreeStatus(branch="feat/test", path=repo_relative, dirty=False, porcelain="")

    def diff(self, repo_relative):
        self.calls.append(("diff", repo_relative))
        return "secret-ish diff body that must not be audited"

    def create_feature_worktree(self, **kwargs):
        self.calls.append(("create", kwargs))
        return WorktreeStatus(branch=kwargs["branch"], path=kwargs["destination_relative"], dirty=False, porcelain="")

    def run_check(self, repo_relative, *, name, argv, allowlisted_checks):
        self.calls.append(("check", repo_relative, name, tuple(argv)))
        return WorktreeCommandResult(exit_code=0, stdout="private output", stderr="")

    def commit(self, worktree_relative, *, message, expected_branch):
        self.calls.append(("commit", worktree_relative, message, expected_branch))
        return WorktreeCommitResult(branch=expected_branch, commit_sha="a" * 40)

    def remove_worktree(self, **kwargs):
        self.calls.append(("remove", kwargs))


class WorkspaceWorktreeServiceTests(unittest.TestCase):
    def setUp(self):
        FakeAdapter.instances.clear()
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()
        self.root = self.settings.workspace_root / "repo-root"
        (self.root / "repo").mkdir(parents=True)
        service = WorkspaceGrantService(self.settings, self.db)
        grant = service.normalize(
            {
                "name": "repo grant",
                "root": "repo-root",
                "read": True,
                "write": True,
                "commands": ["git", "python"],
                "network_policy": "deny",
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(timespec="seconds"),
            }
        )
        self.grant = self.db.upsert_workspace_grant("default", grant, "tester")
        self.authorized = []

        def authorize(tenant_id, actor, action, grant_id):
            self.authorized.append((tenant_id, actor, action, grant_id))

        self.service = WorkspaceWorktreeService(
            self.settings,
            self.db,
            mutation_authorizer=authorize,
            adapter_factory=FakeAdapter,
        )

    def tearDown(self):
        self.engine.shutdown()
        self.temp.cleanup()

    @staticmethod
    def _audit_details_text(rows):
        return "\n".join(json.dumps(row.get("details", {}), sort_keys=True) for row in rows)

    def test_read_operations_resolve_tenant_grant_and_audit_metadata_only(self):
        status = self.service.status("default", "alice", self.grant["id"], "repo")
        self.assertEqual(status.branch, "feat/test")
        diff = self.service.diff("default", "alice", self.grant["id"], "repo")
        self.assertIn("secret-ish", diff)
        adapter = FakeAdapter.instances[-1]
        self.assertEqual(adapter.kwargs["grant_root"], self.root.resolve())
        self.assertTrue(adapter.kwargs["grant_write"])
        self.assertIn("git", adapter.kwargs["grant_commands"])

        audit = self.db.list_audit("default", limit=10)
        joined = self._audit_details_text(audit)
        self.assertNotIn("secret-ish diff body", joined)
        self.assertIn("output_bytes", joined)

    def test_cross_tenant_grant_lookup_fails_closed(self):
        self.db.ensure_tenant("other")
        with self.assertRaisesRegex(Exception, "not found|disabled"):
            self.service.status("other", "mallory", self.grant["id"], "repo")
        self.assertEqual(FakeAdapter.instances, [])

    def test_mutations_require_existing_control_plane_authorizer(self):
        no_authorizer = WorkspaceWorktreeService(self.settings, self.db, adapter_factory=FakeAdapter)
        with self.assertRaisesRegex(WorktreeError, "approval/policy"):
            no_authorizer.create_feature_worktree(
                "default",
                "alice",
                self.grant["id"],
                repo_relative="repo",
                destination_relative="tree-a",
                branch="feat/a",
            )
        self.assertEqual(FakeAdapter.instances, [])

    def test_authorized_create_and_remove_are_durable_and_audited(self):
        created = self.service.create_feature_worktree(
            "default",
            "alice",
            self.grant["id"],
            repo_relative="repo",
            destination_relative="tree-a",
            branch="feat/a",
        )
        self.assertEqual(created.branch, "feat/a")
        rows = self.db.list_workspace_worktrees("default")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "active")
        self.assertEqual(rows[0]["branch"], "feat/a")
        self.assertIsNone(rows[0]["task_id"])
        self.assertEqual(rows[0]["expires_at"], self.grant["expires_at"])

        self.service.remove_worktree(
            "default",
            "alice",
            self.grant["id"],
            repo_relative="repo",
            worktree_relative="tree-a",
        )
        row = self.db.get_workspace_worktree_record("default", rows[0]["id"])
        self.assertEqual(row["status"], "removed")
        self.assertTrue(row["removed_at"])
        actions = [item[2] for item in self.authorized]
        self.assertEqual(actions, ["workspace.worktree.create", "workspace.worktree.remove"])
        audit_actions = [row["action"] for row in self.db.list_audit("default", limit=20)]
        self.assertIn("workspace.worktree.create", audit_actions)
        self.assertIn("workspace.worktree.remove", audit_actions)

    def test_authorized_commit_requires_tracked_worktree_and_audits_no_message(self):
        self.service.create_feature_worktree(
            "default",
            "alice",
            self.grant["id"],
            repo_relative="repo",
            destination_relative="tree-commit",
            branch="feat/commit",
        )
        result = self.service.commit_worktree(
            "default",
            "alice",
            self.grant["id"],
            repo_relative="repo",
            worktree_relative="tree-commit",
            message="private commit message",
        )
        self.assertEqual(result.branch, "feat/commit")
        self.assertEqual(result.commit_sha, "a" * 40)
        self.assertIn(
            ("default", "alice", "workspace.worktree.commit", self.grant["id"]),
            self.authorized,
        )
        joined = self._audit_details_text(self.db.list_audit("default", limit=20))
        self.assertNotIn("private commit message", joined)
        self.assertIn('"commit_sha": "' + ("a" * 40) + '"', joined)

        with self.assertRaisesRegex(WorktreeError, "not tracked"):
            self.service.commit_worktree(
                "default",
                "alice",
                self.grant["id"],
                repo_relative="repo",
                worktree_relative="missing-tree",
                message="feat: missing",
            )

    def test_task_linkage_must_resolve_inside_tenant(self):
        with self.assertRaisesRegex(ValueError, "task not found"):
            self.db.create_workspace_worktree_record(
                "default",
                self.grant["id"],
                "alice",
                repo_relative="repo",
                worktree_relative="tree-task",
                branch="feat/task",
                start_ref="HEAD",
                expires_at=self.grant["expires_at"],
                task_id="missing-task",
            )

    def test_remove_rejects_untracked_or_mismatched_worktree(self):
        with self.assertRaisesRegex(WorktreeError, "not tracked"):
            self.service.remove_worktree(
                "default",
                "alice",
                self.grant["id"],
                repo_relative="repo",
                worktree_relative="unknown-tree",
            )
        self.service.create_feature_worktree(
            "default",
            "alice",
            self.grant["id"],
            repo_relative="repo",
            destination_relative="tree-b",
            branch="feat/b",
        )
        with self.assertRaisesRegex(WorktreeError, "does not match"):
            self.service.remove_worktree(
                "default",
                "alice",
                self.grant["id"],
                repo_relative="other-repo",
                worktree_relative="tree-b",
            )

    def test_expired_cleanup_uses_tracked_record_and_authorizer(self):
        row = self.db.create_workspace_worktree_record(
            "default",
            self.grant["id"],
            "alice",
            repo_relative="repo",
            worktree_relative="tree-expired",
            branch="feat/expired",
            start_ref="HEAD",
            expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(timespec="seconds"),
        )
        result = self.service.cleanup_expired("default", "janitor")
        self.assertEqual(result, {"matched": 1, "removed": 1, "failed": 0})
        current = self.db.get_workspace_worktree_record("default", row["id"])
        self.assertEqual(current["status"], "removed")
        self.assertIn(
            ("default", "janitor", "workspace.worktree.remove", self.grant["id"]),
            self.authorized,
        )

    def test_cross_tenant_lifecycle_rows_are_not_visible(self):
        self.service.create_feature_worktree(
            "default",
            "alice",
            self.grant["id"],
            repo_relative="repo",
            destination_relative="tree-c",
            branch="feat/c",
        )
        self.db.ensure_tenant("other")
        self.assertEqual(self.db.list_workspace_worktrees("other"), [])

    def test_check_audit_excludes_stdout(self):
        result = self.service.run_check(
            "default",
            "alice",
            self.grant["id"],
            "repo",
            name="unit",
            argv=("python", "-m", "unittest"),
            allowlisted_checks={"unit": ("python", "-m", "unittest")},
        )
        self.assertEqual(result.exit_code, 0)
        joined = self._audit_details_text(self.db.list_audit("default", limit=10))
        self.assertNotIn("private output", joined)
        self.assertIn('"exit_code": 0', joined)


if __name__ == "__main__":
    unittest.main()
