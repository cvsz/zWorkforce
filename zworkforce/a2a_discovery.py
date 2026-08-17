from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any
import urllib.parse
import urllib.request


class A2ADiscoveryError(Exception):
    pass


@dataclass(frozen=True)
class AgentCapability:
    name: str
    description: str
    version: str
    tools: tuple[str, ...] = ()
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentManifest:
    agent_id: str
    name: str
    department: str
    description: str
    capabilities: list[AgentCapability] = field(default_factory=list)
    endpoints: dict[str, str] = field(default_factory=dict)


class A2ADiscoveryRegistry:
    """Manages Agent-to-Agent (A2A) discovery manifests and context bus delegation."""
    def __init__(self):
        self._manifests: dict[str, AgentManifest] = {}

    def register_agent(self, manifest: AgentManifest) -> None:
        if not manifest.agent_id:
            raise A2ADiscoveryError("agent_id is required for A2A registration")
        self._manifests[manifest.agent_id] = manifest

    def get_manifest(self, agent_id: str) -> AgentManifest | None:
        return self._manifests.get(agent_id)

    def generate_well_known_manifest(self, base_url: str = "http://127.0.0.1:9569") -> dict[str, Any]:
        """Generates RFC-compliant /.well-known/agent.json manifest catalog."""
        agents_list = []
        for a in self._manifests.values():
            agents_list.append({
                "agent_id": a.agent_id,
                "name": a.name,
                "department": a.department,
                "description": a.description,
                "capabilities": [
                    {
                        "name": c.name,
                        "description": c.description,
                        "version": c.version,
                        "tools": list(c.tools),
                    }
                    for c in a.capabilities
                ],
                "endpoints": a.endpoints or {
                    "task_dispatch": f"{base_url}/api/v1/tasks",
                    "acp": f"{base_url}/acp",
                }
            })
        return {
            "schema_version": "1.0",
            "provider": "zWorkforce",
            "agents": agents_list,
        }

    def match_capable_agents(self, required_tool: str) -> list[AgentManifest]:
        matched = []
        for m in self._manifests.values():
            for c in m.capabilities:
                if required_tool in c.tools:
                    matched.append(m)
                    break
        return matched
