from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Callable


class AgentHandoffError(Exception):
    pass


@dataclass(frozen=True)
class HandoffContract:
    """Defines strict typed inputs and context boundary for subagent delegation."""
    source_agent_id: str
    target_agent_id: str
    required_inputs: tuple[str, ...] = ()
    max_context_tokens: int = 4000
    allow_mutating: bool = False
    validation_schema: dict[str, Any] = field(default_factory=dict)


class AgentHandoffProtocol:
    """Enforces typed handoffs, token budget fencing, and safety escalation guards
    between collaborating agents on Free Model First tiers.
    """
    def __init__(self, contracts: list[HandoffContract] | None = None):
        self._contracts: dict[tuple[str, str], HandoffContract] = {}
        for c in (contracts or []):
            self.register_contract(c)

    def register_contract(self, contract: HandoffContract) -> None:
        key = (contract.source_agent_id, contract.target_agent_id)
        self._contracts[key] = contract

    def validate_handoff(
        self,
        source_agent_id: str,
        target_agent_id: str,
        arguments: dict[str, Any],
        is_mutating: bool = False,
        estimated_tokens: int = 0,
    ) -> dict[str, Any]:
        key = (source_agent_id, target_agent_id)
        contract = self._contracts.get(key)

        # 1. Self-delegation check
        if source_agent_id == target_agent_id:
            raise AgentHandoffError(f"agent {source_agent_id!r} cannot delegate directly to itself")

        # 2. Target presence
        if not target_agent_id:
            raise AgentHandoffError("target agent_id is required for handoff")

        # 3. Contract validation (if defined for the pair)
        if contract:
            # Mutating permissions
            if is_mutating and not contract.allow_mutating:
                raise AgentHandoffError(f"handoff from {source_agent_id} to {target_agent_id} does not permit mutating actions")

            # Context size limit
            if estimated_tokens > contract.max_context_tokens:
                raise AgentHandoffError(
                    f"handoff context tokens ({estimated_tokens}) exceeds maximum contract limit ({contract.max_context_tokens})"
                )

            # Required parameters check
            for req in contract.required_inputs:
                if req not in arguments:
                    raise AgentHandoffError(f"missing required parameter {req!r} for handoff contract to {target_agent_id}")

            # Basic JSON Schema validation if provided
            if contract.validation_schema:
                self._validate_schema(arguments, contract.validation_schema)

        # 4. Context compaction / normalization
        sanitized_args = {}
        for k, v in arguments.items():
            if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                sanitized_args[k] = v
            else:
                sanitized_args[k] = str(v)

        return sanitized_args

    def _validate_schema(self, data: dict[str, Any], schema: dict[str, Any]) -> None:
        required = schema.get("required", [])
        for r in required:
            if r not in data:
                raise AgentHandoffError(f"schema violation: field {r!r} is required")
        properties = schema.get("properties", {})
        for k, prop in properties.items():
            if k in data and "type" in prop:
                expected_type = prop["type"]
                val = data[k]
                if expected_type == "string" and not isinstance(val, str):
                    raise AgentHandoffError(f"schema violation: field {k!r} must be a string")
                elif expected_type == "number" and not isinstance(val, (int, float)):
                    raise AgentHandoffError(f"schema violation: field {k!r} must be a number")
                elif expected_type == "boolean" and not isinstance(val, bool):
                    raise AgentHandoffError(f"schema violation: field {k!r} must be a boolean")
                elif expected_type == "array" and not isinstance(val, list):
                    raise AgentHandoffError(f"schema violation: field {k!r} must be an array")
                elif expected_type == "object" and not isinstance(val, dict):
                    raise AgentHandoffError(f"schema violation: field {k!r} must be an object")
