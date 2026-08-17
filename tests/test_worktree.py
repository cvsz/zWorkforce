from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from zworkforce.worktree import GitWorktreeAdapter, WorktreeError


class Completed:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class RecordingRunner:
    def __init__(self, root: Path):
        self.root = root
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), dict(kwargs)))
        if "rev-parse" in argv:
            if "HEAD" in argv:
                return Completed(stdout="a" * 40 + "\n")
            return Completed(stdout=str(self.root) + "\n")
        if "branch" in argv and "--show-current" in argv:
            return Completed(stdout="feat/example\n")
        if "status" in argv:
            return Completed(stdout="")
        return Completed()


class GitWorktreeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root / "repo").mkdir()
        self.repo = (self.root / "repo").resolve()

    def tearDown(self):
        self.temp.cleanup()

    def adapter(self, **kwargs):
        runner = kwargs.pop("runner", RecordingRunner(self.repo))
        adapter = GitWorktreeAdapter(
            grant_root=self.root,
            grant_write=kwargs.pop("grant_write", True),
            grant_commands=kwargs.pop("grant_commands", ("git", "python")),
            runner=runner,
            git="/usr/bin/git",
            **kwargs,
        )
        return adapter, runner

    def test_rejects_paths_outside_grant(self):
        adapter, _ = self.adapter()
        with self.assertRaises(WorktreeError):
            adapter.repository_root("../outside")
        with self.assertRaises(WorktreeError):
            adapter.create_feature_worktree(
                repo_relative="repo",
                destination_relative="../escape",
                branch="feat/nope",
            )

    def test_rejects_symlink_escape(self):
        outside = Path(self.temp.name).parent
        link = self.root / "escape"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        adapter, _ = self.adapter()
        with self.assertRaises(WorktreeError):
            adapter.repository_root("escape")

    def test_requires_git_grant_and_write_for_mutations(self):
        adapter, _ = self.adapter(grant_commands=("python",))
        with self.assertRaises(WorktreeError):
            adapter.repository_root("repo")

        readonly, _ = self.adapter(grant_write=False)
        with self.assertRaises(WorktreeError):
            readonly.create_feature_worktree(
                repo_relative="repo",
                destination_relative="new-tree",
                branch="feat/read-only",
            )

    def test_protected_and_malformed_branch_names_fail_closed(self):
        adapter, _ = self.adapter()
        for branch in ("main", "master", "../main", "bad branch", "feat//double", "feat/../main"):
            with self.subTest(branch=branch):
                with self.assertRaises(WorktreeError):
                    adapter.create_feature_worktree(
                        repo_relative="repo",
                        destination_relative="new-tree",
                        branch=branch,
                    )

    def test_create_uses_argv_shell_false_and_bounded_environment(self):
        destination = self.root / "new-tree"
        runner = RecordingRunner(self.repo)

        def create_runner(argv, **kwargs):
            runner.calls.append((list(argv), dict(kwargs)))
            if "rev-parse" in argv:
                return Completed(stdout=str(self.repo) + "\n")
            if "worktree" in argv and "add" in argv:
                destination.mkdir()
                return Completed()
            if "branch" in argv:
                return Completed(stdout="feat/example\n")
            if "status" in argv:
                return Completed(stdout="")
            return Completed()

        adapter, _ = self.adapter(runner=create_runner)
        status = adapter.create_feature_worktree(
            repo_relative="repo",
            destination_relative="new-tree",
            branch="feat/example",
            start_ref="HEAD",
        )
        self.assertEqual(status.branch, "feat/example")
        add_call = next(call for call in runner.calls if "worktree" in call[0] and "add" in call[0])
        argv, kwargs = add_call
        self.assertEqual(argv[0], "/usr/bin/git")
        self.assertIn("core.hooksPath=/dev/null", argv)
        self.assertIn("core.fsmonitor=false", argv)
        self.assertIn("-b", argv)
        self.assertEqual(kwargs["shell"], False)
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertNotIn("HOME", kwargs["env"])
        self.assertEqual(kwargs["env"]["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(kwargs["env"]["GIT_CONFIG_GLOBAL"], "/dev/null")
        self.assertEqual(kwargs["env"]["GIT_ATTR_NOSYSTEM"], "1")

    def test_status_and_diff_are_read_only(self):
        adapter, runner = self.adapter(grant_write=False)
        status = adapter.status("repo")
        self.assertEqual(status.branch, "feat/example")
        self.assertFalse(status.dirty)
        self.assertEqual(adapter.diff("repo"), "")
        commands = [call[0] for call in runner.calls]
        self.assertTrue(any("status" in argv for argv in commands))
        diff_call = next(argv for argv in commands if "diff" in argv)
        self.assertIn("--no-ext-diff", diff_call)
        self.assertIn("--no-textconv", diff_call)

    def test_check_requires_exact_operator_allowlist_and_grant_command(self):
        adapter, runner = self.adapter()
        result = adapter.run_check(
            "repo",
            name="unit",
            argv=("python", "-m", "unittest", "tests.test_workspace"),
            allowlisted_checks={"unit": ("python", "-m", "unittest", "tests.test_workspace")},
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(any(call[0][0] == "python" for call in runner.calls))

        with self.assertRaises(WorktreeError):
            adapter.run_check(
                "repo",
                name="unit",
                argv=("python", "-c", "print('not allowlisted')"),
                allowlisted_checks={"unit": ("python", "-m", "unittest", "tests.test_workspace")},
            )

    def test_external_git_helper_config_fails_closed_before_staging(self):
        calls = []

        def malicious_config_runner(argv, **kwargs):
            calls.append((list(argv), dict(kwargs)))
            if "rev-parse" in argv:
                return Completed(stdout=str(self.repo) + "\n")
            if "config" in argv and "--get-regexp" in argv:
                return Completed(stdout="filter.evil.clean /tmp/evil-filter\n")
            return Completed()

        adapter, _ = self.adapter(runner=malicious_config_runner)
        with self.assertRaisesRegex(WorktreeError, "external Git helpers"):
            adapter.commit("repo", message="feat: guarded", expected_branch="feat/example")
        commands = [argv for argv, _ in calls]
        self.assertTrue(any("config" in argv and "--includes" in argv for argv in commands))
        self.assertFalse(any("add" in argv for argv in commands))
        self.assertFalse(any("commit" in argv for argv in commands))

    def test_commit_stages_all_uses_tracked_branch_and_returns_sha(self):
        calls = []
        commit_sha = "a" * 40

        def commit_runner(argv, **kwargs):
            calls.append((list(argv), dict(kwargs)))
            if "rev-parse" in argv and "--show-toplevel" in argv:
                return Completed(stdout=str(self.repo) + "\n")
            if "branch" in argv and "--show-current" in argv:
                return Completed(stdout="feat/example\n")
            if "status" in argv:
                return Completed(stdout=" M app.py\n")
            if "diff" in argv and "--cached" in argv and "--quiet" in argv:
                return Completed(returncode=1)
            if "rev-parse" in argv and "HEAD" in argv:
                return Completed(stdout=commit_sha + "\n")
            return Completed()

        adapter, _ = self.adapter(runner=commit_runner)
        result = adapter.commit("repo", message="feat: bounded commit", expected_branch="feat/example")
        self.assertEqual(result.branch, "feat/example")
        self.assertEqual(result.commit_sha, commit_sha)
        commands = [call[0] for call in calls]
        self.assertTrue(any("add" in argv and "--all" in argv and "--" in argv for argv in commands))
        commit_call = next(call for call in calls if "commit" in call[0])
        self.assertIn("feat: bounded commit", commit_call[0])
        self.assertIn("core.hooksPath=/dev/null", commit_call[0])
        self.assertIn("core.fsmonitor=false", commit_call[0])
        self.assertIn("commit.gpgSign=false", commit_call[0])
        self.assertEqual(commit_call[1]["shell"], False)
        self.assertNotIn("HOME", commit_call[1]["env"])

    def test_commit_fails_closed_for_branch_mismatch_empty_change_and_bad_message(self):
        adapter, _ = self.adapter()
        with self.assertRaisesRegex(WorktreeError, "branch"):
            adapter.commit("repo", message="feat: test", expected_branch="feat/other")
        with self.assertRaisesRegex(WorktreeError, "single non-empty line"):
            adapter.commit("repo", message="line one\nline two", expected_branch="feat/example")

        def empty_runner(argv, **kwargs):
            if "rev-parse" in argv:
                return Completed(stdout=str(self.repo) + "\n")
            if "branch" in argv and "--show-current" in argv:
                return Completed(stdout="feat/example\n")
            if "status" in argv:
                return Completed(stdout="")
            if "diff" in argv and "--cached" in argv:
                return Completed(returncode=0)
            return Completed()

        empty, _ = self.adapter(runner=empty_runner)
        with self.assertRaisesRegex(WorktreeError, "no changes"):
            empty.commit("repo", message="feat: nothing", expected_branch="feat/example")

    def test_remove_refuses_primary_repo_and_uses_double_dash(self):
        child = self.root / "child"
        child.mkdir()
        adapter, runner = self.adapter()
        with self.assertRaises(WorktreeError):
            adapter.remove_worktree(repo_relative="repo", worktree_relative="repo")

        adapter.remove_worktree(repo_relative="repo", worktree_relative="child")
        remove_call = next(call for call in runner.calls if "remove" in call[0])
        self.assertIn("--", remove_call[0])
        self.assertIn("core.hooksPath=/dev/null", remove_call[0])
        self.assertEqual(remove_call[1]["shell"], False)


    def test_get_head_sha_resolves_clean_sha(self):
        adapter, _ = self.adapter()
        sha = adapter.get_head_sha("repo")
        self.assertEqual(sha, "a" * 40)


if __name__ == "__main__":
    unittest.main()
