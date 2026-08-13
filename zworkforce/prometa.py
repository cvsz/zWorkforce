from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from importlib import resources

from .skills import sign_manifest, validate_manifest
from .tools import TOOL_DEFINITIONS
from .workflow import _steps

ROOT = Path(__file__).resolve().parents[1]
PROMETA_AGENTS = ROOT / "examples" / "prometa-agent-catalog.json"
PROMETA_SKILLS = ROOT / "examples" / "prometa-skills.json"
PROMETA_TEMPLATES = ROOT / "examples" / "prometa-agent-templates.json"
PROMETA_WORKFLOWS = ROOT / "examples" / "prometa-workflows.json"
TIERS = {"luna", "terra", "sol"}


class ProMetaError(ValueError):
    pass


def load_prometa_catalog(
    *,
    agents_path: str | Path = PROMETA_AGENTS,
    skills_path: str | Path = PROMETA_SKILLS,
    templates_path: str | Path = PROMETA_TEMPLATES,
    workflows_path: str | Path = PROMETA_WORKFLOWS,
) -> dict[str, list[dict[str, Any]]]:
    catalog = {
        "agents": _read_list(agents_path),
        "skills": _read_list(skills_path),
        "templates": _read_list(templates_path),
        "workflows": _read_list(workflows_path),
    }
    validate_prometa_catalog(catalog)
    return catalog


def validate_prometa_catalog(catalog: dict[str, list[dict[str, Any]]]) -> None:
    skills = catalog.get("skills", [])
    agents = catalog.get("agents", [])
    templates = catalog.get("templates", [])
    workflows = catalog.get("workflows", [])

    skill_ids = set()
    for manifest in skills:
        validate_manifest(manifest)
        if manifest["id"] in skill_ids:
            raise ProMetaError(f"duplicate skill id: {manifest['id']}")
        _validate_tools(manifest.get("allowed_tools", []), f"skill {manifest['id']}")
        skill_ids.add(manifest["id"])

    agent_ids = set()
    for agent in agents:
        _validate_agent(agent, skill_ids)
        if agent["id"] in agent_ids:
            raise ProMetaError(f"duplicate agent id: {agent['id']}")
        agent_ids.add(agent["id"])

    for template in templates:
        template_id = str(template.get("id", "")).strip()
        if not template_id:
            raise ProMetaError("agent template id is required")
        spec = template.get("agent")
        if not isinstance(spec, dict):
            raise ProMetaError(f"agent template {template_id} requires an agent object")
        _validate_agent({**spec, "id": spec.get("id") or template_id}, skill_ids, require_id=False)

    for workflow in workflows:
        _steps(workflow.get("definition") or {})
        for step in workflow["definition"]["steps"]:
            if step["agent_id"] not in agent_ids:
                raise ProMetaError(f"workflow {workflow.get('id')} references unknown agent {step['agent_id']}")


def install_prometa_catalog(
    db,
    tenant_id: str,
    actor: str,
    *,
    signing_key: str = "",
    sign_skills: bool = False,
    agents_path: str | Path = PROMETA_AGENTS,
    skills_path: str | Path = PROMETA_SKILLS,
    templates_path: str | Path = PROMETA_TEMPLATES,
    workflows_path: str | Path = PROMETA_WORKFLOWS,
) -> dict[str, Any]:
    catalog = load_prometa_catalog(
        agents_path=agents_path,
        skills_path=skills_path,
        templates_path=templates_path,
        workflows_path=workflows_path,
    )
    db.ensure_tenant(tenant_id)

    installed_skills = []
    for manifest in catalog["skills"]:
        signature = sign_manifest(manifest, signing_key) if sign_skills else ""
        installed_skills.append(db.upsert_skill(tenant_id, manifest, signature, actor, enabled=True))
        db.audit(tenant_id, actor, "prometa.skill_upsert", "skill", manifest["id"], {"version": manifest["version"], "signed": bool(signature)})

    installed_agents = []
    for agent in catalog["agents"]:
        installed_agents.append(db.upsert_agent(tenant_id, agent, actor))
        db.audit(tenant_id, actor, "prometa.agent_upsert", "agent", agent["id"], {"department": agent.get("department"), "default_tier": agent.get("default_tier")})

    installed_templates = []
    for template in catalog["templates"]:
        installed_templates.append(db.upsert_agent_template(tenant_id, template, actor))
        db.audit(tenant_id, actor, "prometa.agent_template_upsert", "agent_template", template["id"])

    installed_workflows = []
    for workflow in catalog["workflows"]:
        installed_workflows.append(db.upsert_workflow(tenant_id, workflow, actor))
        db.audit(tenant_id, actor, "prometa.workflow_upsert", "workflow", workflow["id"], {"enabled": workflow.get("enabled", True)})

    return {
        "ok": True,
        "tenant_id": tenant_id,
        "skills": len(installed_skills),
        "agents": len(installed_agents),
        "agent_templates": len(installed_templates),
        "workflows": len(installed_workflows),
        "signed_skills": bool(sign_skills),
    }


def _read_list(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if path.exists():
        raw = path.read_text(encoding="utf-8")
    else:
        raw = resources.files("zworkforce").joinpath("prometa_data", path.name).read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
        raise ProMetaError(f"{path} must contain an array of objects")
    return data


def _validate_agent(agent: dict[str, Any], skill_ids: set[str], *, require_id: bool = True) -> None:
    agent_id = str(agent.get("id", "")).strip()
    if require_id and not agent_id:
        raise ProMetaError("agent id is required")
    if not str(agent.get("name", "")).strip():
        raise ProMetaError(f"agent {agent_id or '<template>'} name is required")
    if agent.get("default_tier", "terra") not in TIERS:
        raise ProMetaError(f"agent {agent_id or '<template>'} has invalid default_tier")
    _validate_tools(agent.get("allowed_tools", []), f"agent {agent_id or '<template>'}")
    _validate_tools(agent.get("approval_tools", []), f"agent {agent_id or '<template>'}")
    if not set(map(str, agent.get("approval_tools", []))).issubset(set(map(str, agent.get("allowed_tools", [])))):
        raise ProMetaError(f"agent {agent_id or '<template>'} approval_tools must be a subset of allowed_tools")
    attached = set(map(str, agent.get("skill_ids", [])))
    missing = sorted(attached - skill_ids)
    if missing:
        raise ProMetaError(f"agent {agent_id or '<template>'} references unknown skills: {', '.join(missing)}")
    if bool(agent.get("requires_approval_for_mutations", True)) and int(agent.get("required_approvals", 0)) < 1:
        raise ProMetaError(f"agent {agent_id or '<template>'} mutating agents require at least one approval")


def _validate_tools(tools: Any, owner: str) -> None:
    if not isinstance(tools, list) or any(str(tool) not in TOOL_DEFINITIONS for tool in tools):
        raise ProMetaError(f"{owner} contains an unknown tool")
