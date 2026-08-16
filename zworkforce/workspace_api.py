from __future__ import annotations

import re
import urllib.parse
from typing import Any

from .api import App as CoreApp

NOT_HANDLED = object()
_UUID_PATH = r"[0-9A-Fa-f-]{36}"


def _q(query: dict[str, list[str]], key: str) -> str:
    return str((query.get(key) or [""])[0]).strip()


def _intq(query: dict[str, list[str]], key: str, default: int) -> int:
    try:
        return int((query.get(key) or [str(default)])[0])
    except ValueError as exc:
        raise ValueError(f"query parameter {key} must be an integer") from exc


def _boolean(body: dict[str, Any], key: str, default: bool) -> bool:
    if key not in body:
        return default
    value = body[key]
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _workspace_principal(handler, role: str, scope: str):
    ctx, response = handler._principal(role, scope)
    if response:
        return None
    return ctx


def handle_workspace_get(handler, app, path: str, query: dict[str, list[str]]):
    if not path.startswith("/api/v1/workspaces"):
        return NOT_HANDLED

    ctx = _workspace_principal(handler, "viewer", "workspace:read")
    if ctx is None:
        return None
    _, tenant_id = ctx

    if path == "/api/v1/workspaces/projects":
        return handler._json(200, {
            "items": app.db.list_workspace_projects(
                tenant_id,
                status=_q(query, "status") or None,
                query=_q(query, "q"),
                limit=_intq(query, "limit", 100),
                offset=_intq(query, "offset", 0),
            )
        })

    match = re.fullmatch(rf"/api/v1/workspaces/projects/({_UUID_PATH})", path)
    if match:
        project = app.db.get_workspace_project(tenant_id, match.group(1))
        if not project:
            return handler._error(404, "workspace_project_not_found", "workspace project not found")
        return handler._json(200, project)

    if path == "/api/v1/workspaces/conversations":
        return handler._json(200, {
            "items": app.db.list_workspace_conversations(
                tenant_id,
                query=_q(query, "q"),
                project_id=_q(query, "project_id") or None,
                status=_q(query, "status") or None,
                limit=_intq(query, "limit", 100),
                offset=_intq(query, "offset", 0),
            )
        })

    match = re.fullmatch(rf"/api/v1/workspaces/conversations/({_UUID_PATH})/messages", path)
    if match:
        conversation = app.db.get_workspace_conversation(tenant_id, match.group(1))
        if not conversation:
            return handler._error(404, "workspace_conversation_not_found", "workspace conversation not found")
        return handler._json(200, {
            "items": app.db.list_workspace_messages(
                tenant_id,
                conversation["id"],
                limit=_intq(query, "limit", 200),
                offset=_intq(query, "offset", 0),
            )
        })

    match = re.fullmatch(rf"/api/v1/workspaces/conversations/({_UUID_PATH})", path)
    if match:
        conversation = app.db.get_workspace_conversation(tenant_id, match.group(1))
        if not conversation:
            return handler._error(404, "workspace_conversation_not_found", "workspace conversation not found")
        return handler._json(200, conversation)

    return handler._error(404, "not_found", "not found")


def handle_workspace_post(handler, app, path: str):
    if not path.startswith("/api/v1/workspaces"):
        return NOT_HANDLED

    ctx = _workspace_principal(handler, "operator", "workspace:write")
    if ctx is None:
        return None
    principal, tenant_id = ctx
    body = handler._body()

    if path == "/api/v1/workspaces/projects":
        project = app.db.create_workspace_project(
            tenant_id,
            str(body.get("name", "")),
            principal.name,
            description=str(body.get("description", "")),
            project_id=str(body["id"]) if body.get("id") else None,
        )
        app.db.audit(
            tenant_id,
            principal.name,
            "workspace.project.create",
            "workspace_project",
            project["id"],
            {"name": project["name"][:200]},
        )
        return handler._json(201, project)

    match = re.fullmatch(rf"/api/v1/workspaces/projects/({_UUID_PATH})/(rename|pin|archive)", path)
    if match:
        project_id, action = match.group(1), match.group(2)
        if not app.db.get_workspace_project(tenant_id, project_id):
            return handler._error(404, "workspace_project_not_found", "workspace project not found")
        if action == "rename":
            project = app.db.update_workspace_project(
                tenant_id,
                project_id,
                name=str(body.get("name", "")),
                description=str(body["description"]) if "description" in body else None,
            )
        elif action == "pin":
            project = app.db.update_workspace_project(
                tenant_id,
                project_id,
                pinned=_boolean(body, "pinned", True),
            )
        else:
            project = app.db.update_workspace_project(
                tenant_id,
                project_id,
                status="archived" if _boolean(body, "archived", True) else "active",
            )
        app.db.audit(
            tenant_id,
            principal.name,
            f"workspace.project.{action}",
            "workspace_project",
            project_id,
            {"status": project["status"], "pinned": bool(project["pinned"])},
        )
        return handler._json(200, project)

    if path == "/api/v1/workspaces/conversations":
        conversation = app.db.create_workspace_conversation(
            tenant_id,
            principal.name,
            project_id=str(body["project_id"]) if body.get("project_id") else None,
            title=str(body.get("title", "")),
            conversation_id=str(body["id"]) if body.get("id") else None,
            source_task_id=str(body["source_task_id"]) if body.get("source_task_id") else None,
            source_workflow_run_id=str(body["source_workflow_run_id"]) if body.get("source_workflow_run_id") else None,
            retention_policy=str(body.get("retention_policy", "standard")),
        )
        app.db.audit(
            tenant_id,
            principal.name,
            "workspace.conversation.create",
            "workspace_conversation",
            conversation["id"],
            {
                "project_id": conversation.get("project_id"),
                "source_task_id": conversation.get("source_task_id"),
                "source_workflow_run_id": conversation.get("source_workflow_run_id"),
                "retention_policy": conversation["retention_policy"],
            },
        )
        return handler._json(201, conversation)

    match = re.fullmatch(rf"/api/v1/workspaces/conversations/({_UUID_PATH})/(rename|pin|archive|move)", path)
    if match:
        conversation_id, action = match.group(1), match.group(2)
        if not app.db.get_workspace_conversation(tenant_id, conversation_id):
            return handler._error(404, "workspace_conversation_not_found", "workspace conversation not found")
        if action == "rename":
            conversation = app.db.update_workspace_conversation(
                tenant_id,
                conversation_id,
                title=str(body.get("title", "")),
            )
        elif action == "pin":
            conversation = app.db.update_workspace_conversation(
                tenant_id,
                conversation_id,
                pinned=_boolean(body, "pinned", True),
            )
        elif action == "archive":
            conversation = app.db.update_workspace_conversation(
                tenant_id,
                conversation_id,
                status="archived" if _boolean(body, "archived", True) else "active",
            )
        else:
            if "project_id" not in body:
                raise ValueError("project_id is required for move")
            conversation = app.db.update_workspace_conversation(
                tenant_id,
                conversation_id,
                project_id=body.get("project_id"),
            )
        app.db.audit(
            tenant_id,
            principal.name,
            f"workspace.conversation.{action}",
            "workspace_conversation",
            conversation_id,
            {
                "project_id": conversation.get("project_id"),
                "status": conversation["status"],
                "pinned": bool(conversation["pinned"]),
            },
        )
        return handler._json(200, conversation)

    match = re.fullmatch(rf"/api/v1/workspaces/conversations/({_UUID_PATH})/messages", path)
    if match:
        conversation_id = match.group(1)
        if not app.db.get_workspace_conversation(tenant_id, conversation_id):
            return handler._error(404, "workspace_conversation_not_found", "workspace conversation not found")
        role = str(body.get("role", "user"))
        if role != "user":
            raise ValueError("external workspace message API accepts role=user only")
        message = app.db.append_workspace_message(
            tenant_id,
            conversation_id,
            role,
            principal.name,
            content=str(body.get("content", "")),
            artifact_ids=body.get("artifact_ids"),
            parent_message_id=str(body["parent_message_id"]) if body.get("parent_message_id") else None,
            message_id=str(body["id"]) if body.get("id") else None,
        )
        app.db.audit(
            tenant_id,
            principal.name,
            "workspace.message.append",
            "workspace_message",
            message["id"],
            {
                "conversation_id": conversation_id,
                "ordinal": message["ordinal"],
                "artifact_count": len(message.get("artifact_ids") or []),
            },
        )
        return handler._json(201, message)

    return handler._error(404, "not_found", "not found")


def handle_workspace_delete(handler, app, path: str):
    if not path.startswith("/api/v1/workspaces"):
        return NOT_HANDLED

    ctx = _workspace_principal(handler, "admin", "workspace:delete")
    if ctx is None:
        return None
    principal, tenant_id = ctx

    match = re.fullmatch(rf"/api/v1/workspaces/conversations/({_UUID_PATH})", path)
    if not match:
        return handler._error(404, "not_found", "not found")
    conversation_id = match.group(1)
    conversation = app.db.get_workspace_conversation(tenant_id, conversation_id)
    if not conversation:
        return handler._error(404, "workspace_conversation_not_found", "workspace conversation not found")
    if not app.db.delete_workspace_conversation(tenant_id, conversation_id):
        return handler._error(404, "workspace_conversation_not_found", "workspace conversation not found")
    app.db.audit(
        tenant_id,
        principal.name,
        "workspace.conversation.delete",
        "workspace_conversation",
        conversation_id,
        {"project_id": conversation.get("project_id"), "retention_policy": conversation["retention_policy"]},
    )
    return handler._json(200, {"ok": True, "id": conversation_id})


class WorkspaceApp(CoreApp):
    """Core zWorkforce API plus isolated workspace/project conversation routes."""

    def handler(self):
        app = self
        ParentHandler = super().handler()

        class Handler(ParentHandler):
            def _get_api(self, path: str):
                result = handle_workspace_get(self, app, path, self._query())
                if result is not NOT_HANDLED:
                    return result
                return super()._get_api(path)

            def do_POST(self):
                path = urllib.parse.urlsplit(self.path).path
                if not path.startswith("/api/v1/workspaces"):
                    return super().do_POST()
                self._prepare()
                try:
                    result = handle_workspace_post(self, app, path)
                    if result is not NOT_HANDLED:
                        return result
                    return self._error(404, "not_found", "not found")
                except (ValueError, TypeError) as exc:
                    return self._error(400, "invalid_request", str(exc))
                except Exception as exc:
                    return self._error(500, "internal_error", "internal server error", str(exc))

            def do_DELETE(self):
                self._prepare()
                path = urllib.parse.urlsplit(self.path).path
                try:
                    result = handle_workspace_delete(self, app, path)
                    if result is not NOT_HANDLED:
                        return result
                    return self._error(404, "not_found", "not found")
                except (ValueError, TypeError) as exc:
                    return self._error(400, "invalid_request", str(exc))
                except Exception as exc:
                    return self._error(500, "internal_error", "internal server error", str(exc))

        return Handler
