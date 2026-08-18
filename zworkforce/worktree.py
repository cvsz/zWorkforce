from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
from typing import Callable, Sequence


class WorktreeError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorktreeStatus:
    branch: str
    path: str
    dirty: bool
    porcelain: str


@dataclass(frozen=True)
class WorktreeCommandResult:
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class WorktreeCommitResult:
    branch: str
    commit_sha: str


@dataclass(frozen=True)
class WorktreePullRequestResult:
    branch: str
    base_branch: str
    commit_sha: str
    title: str
    pr_number: int | None
    pr_url: str | None
    draft: bool


class GitWorktreeAdapter:
    """Grant-bounded Git worktree operations for approved local repositories.

    This adapter is intentionally local-only. Authentication, tenant lookup,
    approvals and GitHub PR creation remain at their existing control-plane
    boundaries. Every subprocess is argv-based with ``shell=False``.
    """

    _BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
    _CHECK_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    _EXTERNAL_HELPER_CONFIG = (
        r"^(filter\..*\.(clean|smudge|process)|diff\..*\.(command|textconv))$"
    )

    def __init__(
        self,
        *,
        grant_root: Path,
        grant_write: bool,
        grant_commands: Sequence[str],
        protected_branches: Sequence[str] = ("main", "master"),
        runner: Callable = subprocess.run,
        git: str | None = None,
        timeout_seconds: int = 120,
        max_output_bytes: int = 262_144,
    ):
        self.grant_root = grant_root.resolve(strict=True)
        if not self.grant_root.is_dir():
            raise WorktreeError("workspace grant root must be an existing directory")
        self.grant_write = bool(grant_write)
        self.grant_commands = frozenset(str(item) for item in grant_commands)
        self.protected_branches = frozenset(str(item) for item in protected_branches)
        self.runner = runner
        self.git = git or shutil.which("git") or ""
        self.timeout_seconds = max(1, int(timeout_seconds))
        self.max_output_bytes = max(1, int(max_output_bytes))

    def _require_git(self) -> None:
        if "git" not in self.grant_commands:
            raise WorktreeError("workspace grant does not authorize git")
        if not self.git:
            raise WorktreeError("git executable is unavailable")

    def _require_mutation(self) -> None:
        if not self.grant_write:
            raise WorktreeError("workspace grant is read-only")

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    def _resolve_existing(self, relative: str, *, directory: bool = True) -> Path:
        candidate = Path(str(relative or "."))
        if candidate.is_absolute() or ".." in candidate.parts or any("%2e" in part.lower() for part in candidate.parts):
            raise WorktreeError("path must be relative to the workspace grant root")
        resolved = (self.grant_root / candidate).resolve(strict=True)
        if not self._is_within(resolved, self.grant_root):
            raise WorktreeError("path escapes the workspace grant root")
        if directory and not resolved.is_dir():
            raise WorktreeError("path must resolve to a directory")
        return resolved

    def _resolve_new_directory(self, relative: str) -> Path:
        candidate = Path(str(relative or "").strip())
        if not candidate.parts or candidate.is_absolute() or ".." in candidate.parts or any("%2e" in part.lower() for part in candidate.parts):
            raise WorktreeError("destination must be a non-empty relative path")
        parent = (self.grant_root / candidate.parent).resolve(strict=True)
        if not self._is_within(parent, self.grant_root):
            raise WorktreeError("destination escapes the workspace grant root")
        destination = parent / candidate.name
        if destination.exists() or destination.is_symlink():
            raise WorktreeError("destination already exists")
        return destination

    def _validate_branch(self, branch: str, *, allow_protected: bool = False) -> str:
        value = str(branch or "").strip()
        if not value or not self._BRANCH.fullmatch(value):
            raise WorktreeError("invalid git branch name")
        if value.startswith("/") or value.endswith("/") or "//" in value or ".." in value:
            raise WorktreeError("invalid git branch name")
        if value in self.protected_branches and not allow_protected:
            raise WorktreeError("protected/default branch cannot be used as a task branch")
        return value

    @staticmethod
    def _validate_commit_message(message: str) -> str:
        value = str(message or "").strip()
        if not value or len(value) > 200 or "\n" in value or "\r" in value or "\x00" in value:
            raise WorktreeError("commit message must be a single non-empty line of at most 200 characters")
        return value

    def _run(self, argv: Sequence[str], *, cwd: Path) -> WorktreeCommandResult:
        self._require_git()
        try:
            completed = self.runner(
                [str(item) for item in argv],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
                stdin=subprocess.DEVNULL,
                env={
                    "PATH": "/usr/local/bin:/usr/bin:/bin",
                    "LANG": "C.UTF-8",
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": "/dev/null",
                    "GIT_ATTR_NOSYSTEM": "1",
                },
            )
        except subprocess.TimeoutExpired as exc:
            raise WorktreeError(f"git command timed out after {self.timeout_seconds}s") from exc
        except OSError as exc:
            raise WorktreeError(f"git command could not start: {exc}") from exc
        return WorktreeCommandResult(
            exit_code=int(completed.returncode),
            stdout=str(completed.stdout or "")[-self.max_output_bytes :],
            stderr=str(completed.stderr or "")[-self.max_output_bytes :],
        )

    def _assert_no_external_git_helpers(self, repo: Path) -> None:
        """Fail closed before Git operations that may consult repository attributes.

        Git clean/smudge/process filters and custom diff/textconv drivers can
        execute arbitrary repository-configured programs even when Python uses
        ``shell=False``. System/global Git config and system attributes are also
        excluded by ``_run`` so only repository-local configuration is relevant.
        """
        result = self._run(
            [
                self.git,
                "-C",
                str(repo),
                "config",
                "--includes",
                "--local",
                "--get-regexp",
                self._EXTERNAL_HELPER_CONFIG,
            ],
            cwd=repo,
        )
        if result.exit_code not in (0, 1):
            raise WorktreeError("unable to verify repository Git helper configuration")
        if result.stdout.strip():
            raise WorktreeError("repository-configured external Git helpers are not allowed")

    def repository_root(self, repo_relative: str = ".") -> Path:
        repo = self._resolve_existing(repo_relative)
        result = self._run([self.git, "-C", str(repo), "rev-parse", "--show-toplevel"], cwd=repo)
        if result.exit_code != 0:
            raise WorktreeError("approved path is not a git repository")
        reported = Path(result.stdout.strip()).resolve(strict=True)
        if not self._is_within(reported, self.grant_root):
            raise WorktreeError("git repository root escapes the workspace grant root")
        return reported

    def create_feature_worktree(
        self,
        *,
        repo_relative: str,
        destination_relative: str,
        branch: str,
        start_ref: str = "HEAD",
    ) -> WorktreeStatus:
        self._require_mutation()
        branch = self._validate_branch(branch)
        repo = self.repository_root(repo_relative)
        self._assert_no_external_git_helpers(repo)
        destination = self._resolve_new_directory(destination_relative)
        start = str(start_ref or "HEAD").strip()
        if not start or start.startswith("-") or any(ch.isspace() for ch in start):
            raise WorktreeError("invalid start ref")
        result = self._run(
            [
                self.git,
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "core.fsmonitor=false",
                "-C",
                str(repo),
                "worktree",
                "add",
                "-b",
                branch,
                str(destination),
                start,
            ],
            cwd=repo,
        )
        if result.exit_code != 0:
            raise WorktreeError((result.stderr or result.stdout or "git worktree add failed").strip()[:500])
        return self.status(destination_relative)

    def status(self, worktree_relative: str) -> WorktreeStatus:
        worktree = self.repository_root(worktree_relative)
        self._assert_no_external_git_helpers(worktree)
        branch_result = self._run(
            [self.git, "-C", str(worktree), "branch", "--show-current"], cwd=worktree
        )
        status_result = self._run(
            [
                self.git,
                "-c",
                "core.fsmonitor=false",
                "-C",
                str(worktree),
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            ],
            cwd=worktree,
        )
        if branch_result.exit_code != 0 or status_result.exit_code != 0:
            raise WorktreeError("unable to inspect worktree status")
        porcelain = status_result.stdout
        return WorktreeStatus(
            branch=branch_result.stdout.strip(),
            path=str(worktree.relative_to(self.grant_root)),
            dirty=bool(porcelain.strip()),
            porcelain=porcelain,
        )

    def diff(self, worktree_relative: str, *, staged: bool = False) -> str:
        worktree = self.repository_root(worktree_relative)
        self._assert_no_external_git_helpers(worktree)
        argv = [
            self.git,
            "-C",
            str(worktree),
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--no-color",
        ]
        if staged:
            argv.append("--cached")
        result = self._run(argv, cwd=worktree)
        if result.exit_code != 0:
            raise WorktreeError("unable to inspect worktree diff")
        return result.stdout

    def run_check(
        self,
        worktree_relative: str,
        *,
        name: str,
        argv: Sequence[str],
        allowlisted_checks: dict[str, Sequence[str]],
    ) -> WorktreeCommandResult:
        worktree = self.repository_root(worktree_relative)
        check_name = str(name or "").strip()
        if not self._CHECK_NAME.fullmatch(check_name):
            raise WorktreeError("invalid check name")
        expected = tuple(str(item) for item in allowlisted_checks.get(check_name, ()))
        requested = tuple(str(item) for item in argv)
        if not expected or requested != expected:
            raise WorktreeError("check command is not allowlisted")
        executable = Path(requested[0]).name
        if executable not in self.grant_commands:
            raise WorktreeError("workspace grant does not authorize check executable")
        return self._run(requested, cwd=worktree)

    def commit(self, worktree_relative: str, *, message: str, expected_branch: str) -> WorktreeCommitResult:
        self._require_mutation()
        worktree = self.repository_root(worktree_relative)
        self._assert_no_external_git_helpers(worktree)
        expected = self._validate_branch(expected_branch)
        current = self.status(worktree_relative).branch
        if not current or current != expected:
            raise WorktreeError("worktree branch does not match its tracked task branch")
        commit_message = self._validate_commit_message(message)
        add_result = self._run(
            [
                self.git,
                "-c",
                "core.fsmonitor=false",
                "-C",
                str(worktree),
                "add",
                "--all",
                "--",
                ".",
            ],
            cwd=worktree,
        )
        if add_result.exit_code != 0:
            raise WorktreeError("unable to stage worktree changes")
        staged = self._run(
            [
                self.git,
                "-C",
                str(worktree),
                "diff",
                "--cached",
                "--quiet",
                "--exit-code",
                "--no-ext-diff",
                "--no-textconv",
            ],
            cwd=worktree,
        )
        if staged.exit_code == 0:
            raise WorktreeError("worktree has no changes to commit")
        if staged.exit_code != 1:
            raise WorktreeError("unable to inspect staged worktree changes")
        committed = self._run(
            [
                self.git,
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "commit.gpgSign=false",
                "-C",
                str(worktree),
                "commit",
                "-m",
                commit_message,
            ],
            cwd=worktree,
        )
        if committed.exit_code != 0:
            raise WorktreeError((committed.stderr or committed.stdout or "git commit failed").strip()[:500])
        head = self._run([self.git, "-C", str(worktree), "rev-parse", "HEAD"], cwd=worktree)
        sha = head.stdout.strip()
        if head.exit_code != 0 or not re.fullmatch(r"[0-9a-fA-F]{40,64}", sha):
            raise WorktreeError("unable to resolve committed HEAD")
        return WorktreeCommitResult(branch=current, commit_sha=sha.lower())

    def get_head_sha(self, worktree_relative: str) -> str:
        worktree = self.repository_root(worktree_relative)
        self._assert_no_external_git_helpers(worktree)
        head = self._run([self.git, "-C", str(worktree), "rev-parse", "HEAD"], cwd=worktree)
        sha = head.stdout.strip()
        if head.exit_code != 0 or not re.fullmatch(r"[0-9a-fA-F]{40,64}", sha):
            raise WorktreeError("unable to resolve worktree HEAD commit")
        return sha.lower()

    def remove_worktree(self, *, repo_relative: str, worktree_relative: str) -> None:
        self._require_mutation()
        repo = self.repository_root(repo_relative)
        worktree = self._resolve_existing(worktree_relative)
        if worktree == repo:
            raise WorktreeError("cannot remove the primary repository worktree")
        result = self._run(
            [
                self.git,
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "core.fsmonitor=false",
                "-C",
                str(repo),
                "worktree",
                "remove",
                "--",
                str(worktree),
            ],
            cwd=repo,
        )
        if result.exit_code != 0:
            raise WorktreeError((result.stderr or result.stdout or "git worktree remove failed").strip()[:500])
