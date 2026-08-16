from __future__ import annotations

import fnmatch
import re
import time
from typing import Any

from .engine import Engine
from .tools import ToolError, is_mutating_tool
from .workspace_tool_executor import WorkspaceGrantedToolExecutor


class PolicyError(ValueError):
    pass


def validate_policy(document: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise PolicyError("policy document must be an object")
    default = str(document.get("default", "allow"))
    if default not in {"allow", "deny"}:
        raise PolicyError("policy default must be allow or deny")
    rules = document.get("rules", [])
    if not isinstance(rules, list) or len(rules) > 256:
        raise PolicyError("policy rules must be an array with at most 256 items")
    normalized = []
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise PolicyError("policy rule must be an object")
        effect = str(rule.get("effect", "deny"))
        if effect not in {"allow", "deny"}:
            raise PolicyError("policy rule effect must be allow or deny")
        action = str(rule.get("action", "")).strip()
        if not action or len(action) > 128:
            raise PolicyError("policy rule action is required")
        when = rule.get("when") or {}
        if not isinstance(when, dict):
            raise PolicyError("policy rule when must be an object")
        allowed = {"agent_id", "department", "actor", "mutating", "tier", "tool"}
        if any(k not in allowed for k in when):
            raise PolicyError("policy rule contains unsupported condition")
        normalized.append({"id": str(rule.get("id") or f"rule-{i+1}"), "effect": effect, "action": action, "when": when})
    return {"default": default, "rules": normalized}


def decide(policies: list[dict[str, Any]], action: str, context: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    allowed_seen = False
    default_denied = False
    matched: list[str] = []
    for stored in policies:
        document = validate_policy(stored.get("document") or {})
        if document["default"] == "deny":
            default_denied = True
        for rule in document["rules"]:
            if not fnmatch.fnmatchcase(action, rule["action"]):
                continue
            if not _matches(rule["when"], context):
                continue
            matched.append(f"{stored.get('id','policy')}:{rule['id']}")
            if rule["effect"] == "deny":
                return False, {"reason": "explicit_deny", "matched": matched}
            allowed_seen = True
    if default_denied and not allowed_seen:
        return False, {"reason": "default_deny", "matched": matched}
    return True, {"reason": "allow", "matched": matched}


def _matches(when: dict[str, Any], context: dict[str, Any]) -> bool:
    for key, expected in when.items():
        actual = context.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif isinstance(expected, str) and ("*" in expected or "?" in expected):
            if not fnmatch.fnmatchcase(str(actual or ""), expected):
                return False
        elif expected != actual:
            return False
    return True


class PolicyEngine(Engine):
    """Engine with tenant policy-as-code checks and grant-aware workspace file tools."""

    _WORKSPACE_FILE_TOOLS = {"workspace_list", "workspace_read", "workspace_write"}

    def __init__(self, settings, db, provider):
        super().__init__(settings, db, provider)
        self.tools = WorkspaceGrantedToolExecutor(settings, db)

    def _policy_decision(self, tenant_id: str, action: str, context: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        if not hasattr(self.db, "list_policies"):
            return True, {"reason": "unsupported"}
        return decide(self.db.list_policies(tenant_id, enabled_only=True), action, context)

    def submit(self, tenant_id: str, agent_id: str, prompt: str, *, actor: str, mutating: bool = False,
               tier_override: str | None = None, **kwargs):
        agent = self.db.get_agent(tenant_id, agent_id)
        context = {
            "agent_id": agent_id,
            "department": agent.get("department") if agent else "",
            "actor": actor,
            "mutating": bool(mutating),
            "tier": tier_override or (agent.get("default_tier") if agent else ""),
            "tool": "",
        }
        allowed, decision = self._policy_decision(tenant_id, "task.submit", context)
        if not allowed:
            if hasattr(self.db, "audit"):
                self.db.audit(tenant_id, actor, "policy.deny", "agent", agent_id, {"action": "task.submit", **decision})
            raise PolicyError("task denied by tenant policy")
        return super().submit(tenant_id, agent_id, prompt, actor=actor, mutating=mutating, tier_override=tier_override, **kwargs)

    @staticmethod
    def _workspace_event_args(name: str, args: dict[str, Any]) -> dict[str, Any]:
        event_args: dict[str, Any] = {
            "workspace_id": str(args.get("workspace_id") or ""),
            "path": str(args.get("path") or ("." if name == "workspace_list" else ""))[:4096],
        }
        if name == "workspace_read":
            try:
                event_args["max_bytes"] = int(args.get("max_bytes", 65536))
            except (TypeError, ValueError):
                event_args["max_bytes"] = "invalid"
        if name == "workspace_write":
            event_args["create_parents"] = bool(args.get("create_parents", False))
            event_args["content_bytes"] = len(str(args.get("content", "")).encode("utf-8"))
        return event_args

    def _execute_workspace_file_tool(self, task: dict[str, Any], name: str, args: dict[str, Any]) -> Any:
        started = time.monotonic()
        success = False
        error = ""
        try:
            result = self.tools.execute(
                name,
                args,
                tenant_id=task["tenant_id"],
                agent_id=task["agent_id"],
                actor=f"agent:{task['agent_id']}",
            )
            success = True
            return result
        except (ToolError, OSError, ValueError) as exc:
            error = str(exc)
            return {"error": error}
        finally:
            self.db.record_tool_event(
                task["tenant_id"],
                task["id"],
                task["agent_id"],
                name,
                is_mutating_tool(name),
                success,
                (time.monotonic() - started) * 1000,
                self._workspace_event_args(name, args),
                error,
            )

    def _execute_tool(self, task: dict[str, Any], name: str, args: dict[str, Any]) -> Any:
        agent = self.db.get_agent(task["tenant_id"], task["agent_id"]) or {}
        context = {
            "agent_id": task["agent_id"],
            "department": agent.get("department", ""),
            "actor": f"agent:{task['agent_id']}",
            "mutating": bool(task.get("mutating")),
            "tier": task.get("tier", ""),
            "tool": name,
        }
        allowed, decision = self._policy_decision(task["tenant_id"], f"tool.{name}", context)
        if not allowed:
            if hasattr(self.db, "audit"):
                self.db.audit(task["tenant_id"], "runtime", "policy.deny", "task", task["id"], {"action": f"tool.{name}", **decision})
            return {"error": f"tool {name!r} denied by tenant policy"}
        if name in self._WORKSPACE_FILE_TOOLS:
            return self._execute_workspace_file_tool(task, name, args)
        return super()._execute_tool(task, name, args)
