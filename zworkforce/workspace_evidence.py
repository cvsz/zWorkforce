from __future__ import annotations

from datetime import datetime
from typing import Any

from .security import SENSITIVE_KEYS

EVENT_LIMIT = 500
TOOL_LIMIT = 500
ARTIFACT_LIMIT = 500
SUBTASK_LIMIT = 200
WORKFLOW_REF_LIMIT = 100


def _duration_ms(task: dict[str, Any]) -> float | None:
    if not task.get("started_at") or not task.get("finished_at"):
        return None
    try:
        return max(0.0, (datetime.fromisoformat(task["finished_at"]) - datetime.fromisoformat(task["started_at"])).total_seconds() * 1000)
    except (TypeError, ValueError):
        return None


def _arg_shape(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in SENSITIVE_KEYS or any(word in lowered for word in ("secret", "token", "password", "api_key", "credential", "cookie")):
                out[str(key)] = {"type": "redacted"}
            else:
                out[str(key)] = _arg_shape(item)
        return out
    if isinstance(value, list):
        return {"type": "list", "items": len(value)}
    if isinstance(value, tuple):
        return {"type": "tuple", "items": len(value)}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, (int, float)):
        return {"type": "number"}
    if value is None:
        return {"type": "null"}
    return {"type": "string", "length": min(len(str(value)), 1_000_000)}


def _task_summary(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": task["id"],
        "agent_id": task["agent_id"],
        "status": task["status"],
        "tier": task.get("tier"),
        "model": task.get("model"),
        "provider_name": task.get("provider_name") or "",
        "mutating": bool(task.get("mutating")),
        "parent_task_id": task.get("parent_task_id"),
        "depth": int(task.get("depth") or 0),
        "required_approvals": int(task.get("required_approvals") or 0),
        "attempt": int(task.get("attempt") or 0),
        "max_attempts": int(task.get("max_attempts") or 0),
        "input_tokens": int(task.get("input_tokens") or 0),
        "cached_tokens": int(task.get("cached_tokens") or 0),
        "output_tokens": int(task.get("output_tokens") or 0),
        "cost_credits": float(task.get("cost_credits") or 0),
        "iterations": int(task.get("iterations") or 0),
        "cancel_requested": bool(task.get("cancel_requested")),
        "outcome_status": task.get("outcome_status"),
        "outcome_score": task.get("outcome_score"),
        "has_result": bool(task.get("result")),
        "has_error": bool(task.get("error")),
        "created_at": task.get("created_at"),
        "updated_at": task.get("updated_at"),
        "started_at": task.get("started_at"),
        "finished_at": task.get("finished_at"),
        "duration_ms": _duration_ms(task),
    }


def _next_actions(task: dict[str, Any], artifacts: list[dict[str, Any]]) -> list[str]:
    status = str(task.get("status") or "")
    if status == "waiting_approval":
        return ["review_approvals"]
    if status in {"failed", "dead_letter"}:
        return ["inspect_failure_evidence", "retry_if_policy_allows"]
    if status == "running":
        return ["monitor_execution"]
    if status == "queued":
        return ["monitor_queue"]
    if status == "canceled":
        return ["review_cancellation"]
    if status == "succeeded":
        return (["review_artifacts"] if artifacts else []) + ["continue_from_result"]
    return []


def build_task_evidence_sidecar(db, tenant_id: str, task_id: str) -> dict[str, Any] | None:
    task = db.get_task(tenant_id, task_id)
    if not task:
        return None

    events = db.list_task_events(tenant_id, task_id, EVENT_LIMIT)
    approvals = db.list_approvals(tenant_id, task_id)
    tools = db.list_tool_events(tenant_id, task_id, TOOL_LIMIT)
    artifacts = db.list_task_artifacts(tenant_id, task_id, ARTIFACT_LIMIT)
    children = db.list_child_tasks(tenant_id, task_id, SUBTASK_LIMIT)
    workflow_refs = db.list_workflow_refs_for_task(tenant_id, task_id, WORKFLOW_REF_LIMIT)

    artifact_projection = [
        {
            "id": item["id"],
            "name": item["name"],
            "content_type": item.get("content_type"),
            "sha256": item.get("sha256"),
            "size_bytes": int(item.get("size_bytes") or 0),
            "metadata_keys": sorted(str(key) for key in (item.get("metadata") or {}).keys()),
            "created_by": item.get("created_by"),
            "created_at": item.get("created_at"),
        }
        for item in artifacts
    ]

    returned_counts = {
        "events": len(events),
        "approvals": len(approvals),
        "tool_calls": len(tools),
        "artifacts": len(artifacts),
        "subtasks": len(children),
        "workflow_refs": len(workflow_refs),
    }
    limits = {
        "events": EVENT_LIMIT,
        "tool_calls": TOOL_LIMIT,
        "artifacts": ARTIFACT_LIMIT,
        "subtasks": SUBTASK_LIMIT,
        "workflow_refs": WORKFLOW_REF_LIMIT,
    }

    return {
        "task": _task_summary(task),
        "timeline": [
            {"id": item.get("id"), "event_type": item.get("event_type"), "actor": item.get("actor"), "created_at": item.get("created_at")}
            for item in events
        ],
        "approvals": [
            {"id": item.get("id"), "actor": item.get("actor"), "decision": item.get("decision"), "created_at": item.get("created_at")}
            for item in approvals
        ],
        "tool_calls": [
            {
                "id": item.get("id"),
                "tool_name": item.get("tool_name"),
                "mutating": bool(item.get("mutating")),
                "success": bool(item.get("success")),
                "duration_ms": float(item.get("duration_ms") or 0),
                "argument_shape": _arg_shape(item.get("args") or {}),
                "has_error": bool(item.get("error")),
                "created_at": item.get("created_at"),
            }
            for item in tools
        ],
        "artifacts": artifact_projection,
        "subtasks": [_task_summary(item) for item in children],
        "workflow_refs": workflow_refs,
        "returned_counts": returned_counts,
        "limits": limits,
        "possibly_truncated": {name: returned_counts[name] >= limit for name, limit in limits.items()},
        "next_actions": _next_actions(task, artifacts),
    }
