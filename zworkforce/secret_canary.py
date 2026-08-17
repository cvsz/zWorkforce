from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
import re
import secrets
from typing import Any


class CanaryLeakError(Exception):
    pass


class SecretCanaryRegistry:
    """Injects and tracks canary tokens across provider configuration and detects
    accidental plaintext disclosure in logs, traces, and API responses.
    """
    CANARY_PREFIX = "zwf-canary-"

    def __init__(self):
        self._tokens: dict[str, str] = {}  # slot_name -> canary_token

    def inject_canary(self, slot_name: str) -> str:
        token = f"{self.CANARY_PREFIX}{secrets.token_hex(16)}"
        self._tokens[slot_name] = token
        return token

    def get_canary(self, slot_name: str) -> str | None:
        return self._tokens.get(slot_name)

    def scan_for_leaks(self, text_payload: str, halt_on_leak: bool = True) -> list[str]:
        """Scans payload text for any active canary tokens."""
        if not text_payload or not isinstance(text_payload, str):
            return []

        detected_leaks: list[str] = []
        for slot, token in self._tokens.items():
            if token in text_payload:
                detected_leaks.append(slot)

        if detected_leaks and halt_on_leak:
            raise CanaryLeakError(
                f"FATAL SECURITY VIOLATION: Secret canary token for slot(s) {detected_leaks} detected in output payload!"
            )

        return detected_leaks

    def redact_canaries(self, text_payload: str) -> str:
        if not text_payload:
            return ""
        result = text_payload
        for token in self._tokens.values():
            result = result.replace(token, "[CANARY_REDACTED]")
        return result
