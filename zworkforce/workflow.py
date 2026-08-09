from __future__ import annotations

import re
from typing import Any


class WorkflowError(ValueError):
    pass


_TOKEN = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


def _steps(definition: dict[str, Any]) -> list[dict[str, Any]]:
    steps = definition.get("steps")
    if not isinstance(steps, list) or not steps:
        raise WorkflowError("workflow definition.steps must be a non-empty array")
    ids: set[str] = set()
    out: list[dict[str, Any]] = []
    for raw in steps:
        if not isinstance(raw, dict):
            raise WorkflowError("workflow step must be an object")
        sid = str(raw.get("id", "")).strip()
        agent = str(raw.get("agent_id", "")).strip()
        prompt = str(raw.get("prompt", ""))
        deps = raw.get("depends_on", [])
        if not sid or sid in ids:
            raise WorkflowError("workflow step ids must be unique and non-empty")
        if not agent or not prompt.strip():
            raise WorkflowError(f"step {sid} requires agent_id and prompt")
        if not isinstance(deps, list) or any(not isinstance(x, str) for x in deps):
            raise WorkflowError(f"step {sid} depends_on must be an array of ids")
        ids.add(sid)
        item = dict(raw)
        item["id"] = sid
        item["agent_id"] = agent
        item["depends_on"] = list(deps)
        out.append(item)
    for step in out:
        unknown = [x for x in step["depends_on"] if x not in ids]
        if unknown:
            raise WorkflowError(f"step {step['id']} has unknown dependencies: {unknown}")
    visiting: set[str] = set()
    visited: set[str] = set()
    by_id = {x["id"]: x for x in out}
    def visit(sid: str) -> None:
        if sid in visiting:
            raise WorkflowError("workflow contains a dependency cycle")
        if sid in visited:
            return
        visiting.add(sid)
        for dep in by_id[sid]["depends_on"]:
            visit(dep)
        visiting.remove(sid)
        visited.add(sid)
    for sid in by_id:
        visit(sid)
    return out


def _lookup(context: dict[str, Any], path: str) -> Any:
    cur: Any = context
    for part in path.strip().split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return ""
    return cur


def _render(text: str, context: dict[str, Any]) -> str:
    def repl(match: re.Match[str]) -> str:
        value = _lookup(context, match.group(1))
        if isinstance(value, (dict, list)):
            import json
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return str(value)
    return _TOKEN.sub(repl, text)


class WorkflowOrchestrator:
    def __init__(self, db, engine):
        self.db = db
        self.engine = engine

    def upsert(self, tenant_id: str, workflow: dict[str, Any], actor: str) -> dict[str, Any]:
        if not isinstance(workflow, dict) or not str(workflow.get("id", "")).strip():
            raise WorkflowError("workflow id is required")
        definition = workflow.get("definition")
        if not isinstance(definition, dict):
            raise WorkflowError("workflow definition is required")
        validated = dict(definition)
        validated["steps"] = _steps(definition)
        payload = dict(workflow)
        payload["id"] = str(payload["id"]).strip()
        payload["definition"] = validated
        return self.db.upsert_workflow(tenant_id, payload, actor)

    def start(self, tenant_id: str, workflow_id: str, input_data: dict[str, Any], actor: str) -> dict[str, Any]:
        workflow = self.db.get_workflow(tenant_id, workflow_id)
        if not workflow or not workflow.get("enabled", 1):
            raise WorkflowError("workflow not found or disabled")
        if not isinstance(input_data, dict):
            raise WorkflowError("workflow input must be an object")
        _steps(workflow["definition"])
        return self.db.create_workflow_run(tenant_id, workflow, actor, input_data)

    def tick(self, tenant_id: str | None = None) -> dict[str, int]:
        stats = {"runs": 0, "tasks_submitted": 0, "completed": 0, "failed": 0}
        for run in self.db.active_workflow_runs(tenant_id):
            stats["runs"] += 1
            steps = self.db.list_workflow_steps(run["id"])
            by_id = {s["step_id"]: s for s in steps}
            context: dict[str, Any] = {"input": run.get("input") or {}, "steps": {}}
            terminal_failure = False
            all_succeeded = True

            for step in steps:
                task_id = step.get("task_id")
                if task_id and step["status"] in {"submitted", "running", "pending"}:
                    task = self.db.get_task(run["tenant_id"], task_id)
                    if task:
                        status = task["status"]
                        if status == "succeeded":
                            result = task.get("result") or ""
                            self.db.update_workflow_step(run["id"], step["step_id"], status="succeeded", result=result)
                            step["status"] = "succeeded"; step["result"] = result
                        elif status in {"failed", "dead_letter", "canceled"}:
                            err = task.get("error") or status
                            self.db.update_workflow_step(run["id"], step["step_id"], status="failed", error=err)
                            step["status"] = "failed"; step["error"] = err
                        elif status in {"queued", "waiting_approval", "running"}:
                            step["status"] = "running"

                if step["status"] == "succeeded":
                    context["steps"][step["step_id"]] = {"result": step.get("result") or ""}
                elif step["status"] == "failed":
                    terminal_failure = True
                    all_succeeded = False
                else:
                    all_succeeded = False

            if terminal_failure:
                self.db.finish_workflow_run(run["id"], "failed", context, "one or more workflow steps failed")
                stats["failed"] += 1
                continue

            for step in steps:
                if step["status"] != "pending" or step.get("task_id"):
                    continue
                deps = step.get("depends_on") or []
                if not all(by_id[d]["status"] == "succeeded" for d in deps):
                    continue
                definition = step.get("definition") or {}
                prompt = _render(str(definition.get("prompt", "")), context)
                task, _ = self.engine.submit(
                    run["tenant_id"], step["agent_id"], prompt,
                    actor=run.get("actor") or "workflow",
                    mutating=bool(definition.get("mutating", False)),
                    tier_override=definition.get("tier"),
                    priority=int(definition.get("priority", 0)),
                    success_criteria=definition.get("success_criteria"),
                    max_attempts=definition.get("max_attempts"),
                    idempotency_key=f"workflow:{run['id']}:{step['step_id']}",
                )
                self.db.update_workflow_step(run["id"], step["step_id"], status="submitted", task_id=task["id"])
                step["status"] = "submitted"; step["task_id"] = task["id"]
                stats["tasks_submitted"] += 1

            refreshed = self.db.list_workflow_steps(run["id"])
            if refreshed and all(x["status"] == "succeeded" for x in refreshed):
                final_context = {"input": run.get("input") or {}, "steps": {x["step_id"]: {"result": x.get("result") or ""} for x in refreshed}}
                self.db.finish_workflow_run(run["id"], "succeeded", final_context)
                stats["completed"] += 1
        return stats
