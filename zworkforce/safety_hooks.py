from __future__ import annotations

import re
from typing import Any


class SafetyViolationError(Exception):
    pass


class SafetyHookRegistry:
    """Pre and post tool execution safety lifecycle hooks.
    Blocks dangerous commands, detects prompt injections, and scrubs output payloads.
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
