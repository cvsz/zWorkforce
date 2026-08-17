from __future__ import annotations

import re
from typing import Any


class SafetyHookError(RuntimeError):
    """Raised when a deterministic safety guard blocks execution."""
    pass


# Protected git branches where autonomous code mutations are prohibited
PROTECTED_BRANCHES: tuple[str, ...] = ("main", "master", "release", "prod", "production")

# Patterns indicating plaintext credential leaks or secret exposure
SECRET_PATTERNS = re.compile(
    r"(?i)(?:api[_-]?key|secret|token|password|auth|bearer)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\.]{12,}['\"]?|"
    r"\b(?:sk|zwf|ghp|gho|glpat|npm|aws|gsk)_[A-Za-z0-9_\-]{16,}\b|"
    r"-----BEGIN (?:RSA|OPENSSH|EC|DSA|PGP|PRIVATE) KEY-----",
)

# Destructive command patterns that fail closed in tool arguments
DESTRUCTIVE_COMMAND_PATTERNS = re.compile(
    r"(?:rm\s+-(?:[a-zA-Z]*f[a-zA-Z]*\s+|[a-zA-Z]*r[a-zA-Z]*\s+)+[/~]|mkfs|dd\s+if=|:\(\)\s*\{\s*:\|:&\s*\};:|chmod\s+-R\s+777\s+/|drop\s+database|format\s+[a-zA-Z]:)",
    re.I,
)


class SafetyLifecycleHooks:
    """Deterministic AST & runtime safety lifecycle hooks for tool executions."""

    @staticmethod
    def is_read_only(tool_name: str) -> bool:
        """Returns True if the tool is strictly read-only and free of side effects."""
        return tool_name in {
            "calculator",
            "workspace_list",
            "workspace_read",
            "memory_search",
            "http_get",
        }

    @staticmethod
    def branch_guard(target_branch: str | None, mutating: bool) -> None:
        """Blocks mutation requests targeted at protected git branches."""
        if not mutating or not target_branch:
            return
        clean_branch = target_branch.strip().lower()
        for protected in PROTECTED_BRANCHES:
            if clean_branch == protected or clean_branch.startswith(f"{protected}/") or clean_branch.startswith(f"release/"):
                raise SafetyHookError(
                    f"branch-guard blocked mutation on protected branch '{target_branch}'. "
                    f"Work must be performed in an isolated feature branch or git worktree."
                )

    @staticmethod
    def secret_guard(content: str) -> None:
        """Scans payload content or command arguments for leaked plaintext secrets."""
        if not content:
            return
        if match := SECRET_PATTERNS.search(content):
            raise SafetyHookError(
                f"secret-guard detected potential credential leak in payload matching pattern: {match.group(0)[:12]}..."
            )

    @staticmethod
    def destructive_guard(command_str: str) -> None:
        """Blocks destructive system-level operations in shell/process invocations."""
        if not command_str:
            return
        if match := DESTRUCTIVE_COMMAND_PATTERNS.search(command_str):
            raise SafetyHookError(
                f"destructive-guard blocked potentially destructive command: '{match.group(0)}'"
            )

    @classmethod
    def pre_tool_execute(
        cls,
        tool_name: str,
        args: dict[str, Any],
        mutating: bool = False,
        current_branch: str | None = None,
    ) -> None:
        """Pre-execution hook checking branch, secret, and destructive guards."""
        if mutating and current_branch:
            cls.branch_guard(current_branch, mutating=True)

        # Inspect string arguments for destructive patterns or secret leaks
        args_dump = str(args)
        cls.destructive_guard(args_dump)
        cls.secret_guard(args_dump)
