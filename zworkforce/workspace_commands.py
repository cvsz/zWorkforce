from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class WorkspaceCommand:
    name: str
    description: str
    role: str
    scope: str
    target: str
    mutating: bool = False

    def public(self) -> dict:
        return asdict(self)


COMMANDS: tuple[WorkspaceCommand, ...] = (
    WorkspaceCommand("plan", "Create or refine an execution plan through the task boundary.", "operator", "task:write", "task.plan", True),
    WorkspaceCommand("review", "Inspect task, workflow, artifact and approval evidence.", "viewer", "workforce:read", "workspace.review"),
    WorkspaceCommand("compact", "Create an explicit durable context-compaction snapshot.", "operator", "workspace:compact", "workspace.compact", True),
    WorkspaceCommand("goal", "Update the active workspace goal/context intent.", "operator", "workspace:write", "workspace.goal", True),
    WorkspaceCommand("status", "Inspect current workspace/task execution status.", "viewer", "workforce:read", "workspace.status"),
    WorkspaceCommand("artifacts", "Inspect durable artifacts associated with the current work.", "viewer", "workforce:read", "workspace.artifacts"),
    WorkspaceCommand("cost", "Inspect budget, usage and chargeback context.", "viewer", "workforce:read", "workspace.cost"),
    WorkspaceCommand("skill", "Manage or invoke a governed skill through the skill boundary.", "admin", "skill:write", "skill.manage", True),
    WorkspaceCommand("workflow", "Create or update a governed workflow through the automation boundary.", "admin", "automation:write", "workflow.manage", True),
    WorkspaceCommand("feedback", "Record operator feedback for the active workspace context.", "operator", "workspace:write", "workspace.feedback", True),
)

COMMAND_BY_NAME = {item.name: item for item in COMMANDS}
MAX_COMMAND_TEXT = 16_384
MAX_ARGUMENT_TEXT = 12_000


def list_workspace_commands() -> list[WorkspaceCommand]:
    return list(COMMANDS)


def parse_workspace_command(text: str) -> tuple[WorkspaceCommand, str]:
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("command text is required")
    if len(raw) > MAX_COMMAND_TEXT:
        raise ValueError(f"command text must be at most {MAX_COMMAND_TEXT} characters")
    if not raw.startswith("/"):
        raise ValueError("workspace command must start with /")
    head, _, argument = raw[1:].partition(" ")
    name = head.strip().lower()
    if not name:
        raise ValueError("workspace command name is required")
    command = COMMAND_BY_NAME.get(name)
    if command is None:
        known = ", ".join(f"/{item.name}" for item in COMMANDS)
        raise ValueError(f"unknown workspace command /{name}; available commands: {known}")
    argument = argument.strip()
    if len(argument) > MAX_ARGUMENT_TEXT:
        raise ValueError(f"command arguments must be at most {MAX_ARGUMENT_TEXT} characters")
    return command, argument
