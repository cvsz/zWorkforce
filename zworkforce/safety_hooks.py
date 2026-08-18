from __future__ import annotations

import re
from typing import Any


class SafetyHookError(RuntimeError):
    """Raised when a deterministic safety guard blocks execution."""
    pass


class SafetyViolationError(Exception):
    """Raised when a registry safety hook blocks a tool invocation."""
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
    r"(?:rm\s+-[a-zA-Z0-9_-]*[rf][a-zA-Z0-9_-]*\s+[/~]|mkfs|dd\s+if=|:\(\)\s*\{\s*:\|:&\s*\};:|chmod\s+-R\s+777\s+/|drop\s+database|format\s+[a-zA-Z]:)",
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


class SafetyHookRegistry:
    """Pre and post tool execution safety lifecycle hooks.

    Blocks dangerous commands, detects prompt injections, and scrubs output
    payloads. Complements the deterministic :class:`SafetyLifecycleHooks` API;
    both are importable so existing tool-execution paths remain unchanged.
    """
    DANGEROUS_PATTERNS = [
        re.compile(r"\brm\s+-(?:rf|fr)\s+/(?:\s|$|\*)"),
        re.compile(r"\bmkfs\b"),
        re.compile(r"\bdd\s+if="),
        re.compile(r">\s*/dev/sd[a-z]"),
        re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),  # Fork bomb
        re.compile(r"\bDROP\s+DATABASE\b", re.IGNORECASE),
        re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
    ]

    PII_PATTERNS = [
        (re.compile(r"\b(?:\d{4}-){3}\d{4}\b"), "[CREDIT_CARD_REDACTED]"),
        (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN_REDACTED]"),
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL_REDACTED]"),
    ]

    def pre_tool_hook(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Inspects tool invocation before execution. Raises SafetyViolationError if dangerous."""
        if tool_name in {"run_command", "bash", "execute_command"}:
            cmd = str(arguments.get("CommandLine") or arguments.get("command") or "")
            for pattern in self.DANGEROUS_PATTERNS:
                if pattern.search(cmd):
                    raise SafetyViolationError(f"Pre-tool security policy blocked dangerous command: {cmd!r}")

        if tool_name in {"sql_query", "db_execute"}:
            query = str(arguments.get("query") or arguments.get("sql") or "")
            for pattern in self.DANGEROUS_PATTERNS:
                if pattern.search(query):
                    raise SafetyViolationError(f"Pre-tool security policy blocked destructive database query: {query!r}")

    def post_tool_hook(self, tool_name: str, result_payload: str) -> str:
        """Sanitizes output payload before returning to the model."""
        if not isinstance(result_payload, str):
            return result_payload

        sanitized = result_payload
        for pattern, replacement in self.PII_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        return sanitized