from __future__ import annotations

import re
import urllib.parse

from .workspace_api import WorkspaceApp

_UUID_PATH = r"[0-9A-Fa-f-]{36}"
_CONTEXT_PREFIX = "/api/v1/workspaces"


def _principal(handler, role: str, scope: str):
    ctx, response = handler._principal(role, scope)
    if response:
        return None
    return ctx


def _intq(query: dict[str, list[str]], key: str, default: int) -> int:
    try:
        return int((query.get(key) or [str(default)])[0])
    except ValueError as exc:
        raise ValueError(f"query parameter {key} must be an integer") from exc


def _audit_snapshot(app, tenant_id: str, actor: str, action: str, snapshot: dict) -> None:
    app.db.audit(
        tenant_id,
        actor,
        action,
        "workspace_context_snapshot",
        snapshot["id"],
        {
            "conversation_id": snapshot["conversation_id"],
            "model_id": snapshot["model_id"],
            "estimated_tokens": int(snapshot["estimated_tokens"]),
            "context_ceiling_tokens": int(snapshot["context_ceiling_tokens"]),
            "compaction_threshold_tokens": int(snapshot["compaction_threshold_tokens"]),
            "member_count": len(snapshot.get("members") or []),
            "summary_sha256": snapshot.get("summary_sha256") or "",
            "reason": snapshot.get("reason") or "",
        },
    )


def handle_context_get(handler, app, path: str, query: dict[str, list[str]]):
    snapshot_match = re.fullmatch(rf"{_CONTEXT_PREFIX}/context-snapshots/({_UUID_PATH})", path)
    list_match = re.fullmatch(rf"{_CONTEXT_PREFIX}/conversations/({_UUID_PATH})/context-snapshots", path)
    if not snapshot_match and not list_match:
        return False

    ctx = _principal(handler, "viewer", "workspace:read")
    if ctx is None:
        return True
    _, tenant_id = ctx

    if snapshot_match:
        snapshot = app.db.get_workspace_context_snapshot(tenant_id, snapshot_match.group(1))
        if not snapshot:
            handler._error(404, "workspace_context_snapshot_not_found", "workspace context snapshot not found")
            return True
        handler._json(200, snapshot)
        return True

    conversation_id = list_match.group(1)
    try:
        items = app.db.list_workspace_context_snapshots(
            tenant_id,
            conversation_id,
            limit=_intq(query, "limit", 100),
        )
    except ValueError as exc:
        if str(exc) == "conversation not found":
            handler._error(404, "workspace_conversation_not_found", "workspace conversation not found")
            return True
        raise
    handler._json(200, {"items": items})
    return True


def handle_context_post(handler, app, path: str):
    compact_match = re.fullmatch(rf"{_CONTEXT_PREFIX}/conversations/({_UUID_PATH})/compact", path)
    snapshot_match = re.fullmatch(rf"{_CONTEXT_PREFIX}/conversations/({_UUID_PATH})/context-snapshots", path)
    if not compact_match and not snapshot_match:
        return False

    required_scope = "workspace:compact" if compact_match else "workspace:write"
    ctx = _principal(handler, "operator", required_scope)
    if ctx is None:
        return True
    principal, tenant_id = ctx
    body = handler._body()
    conversation_id = (compact_match or snapshot_match).group(1)

    if compact_match:
        snapshot = app.db.compact_workspace_conversation(
            tenant_id,
            conversation_id,
            principal.name,
            model_id=str(body.get("model_id", "")),
            context_ceiling_tokens=body.get("context_ceiling_tokens"),
            compaction_threshold_tokens=body.get("compaction_threshold_tokens"),
            summary=str(body.get("summary", "")),
            message_ids=body.get("message_ids"),
            reason=str(body.get("reason") or "manual-compact"),
        )
        _audit_snapshot(app, tenant_id, principal.name, "workspace.context.compact", snapshot)
        handler._json(201, snapshot)
        return True

    snapshot = app.db.create_workspace_context_snapshot(
        tenant_id,
        conversation_id,
        principal.name,
        model_id=str(body.get("model_id", "")),
        context_ceiling_tokens=body.get("context_ceiling_tokens"),
        compaction_threshold_tokens=body.get("compaction_threshold_tokens"),
        message_ids=body.get("message_ids"),
        reason=str(body.get("reason") or "context-checkpoint"),
        summary=str(body.get("summary", "")),
        snapshot_id=str(body["id"]) if body.get("id") else None,
    )
    _audit_snapshot(app, tenant_id, principal.name, "workspace.context.snapshot", snapshot)
    handler._json(201, snapshot)
    return True


class WorkspaceContextApp(WorkspaceApp):
    """Workspace API plus authenticated context snapshot/compaction routes."""

    def handler(self):
        app = self
        ParentHandler = super().handler()

        class Handler(ParentHandler):
            def _get_api(self, path: str):
                if handle_context_get(self, app, path, self._query()):
                    return None
                return super()._get_api(path)

            def do_POST(self):
                path = urllib.parse.urlsplit(self.path).path
                if not (
                    re.fullmatch(rf"{_CONTEXT_PREFIX}/conversations/({_UUID_PATH})/compact", path)
                    or re.fullmatch(rf"{_CONTEXT_PREFIX}/conversations/({_UUID_PATH})/context-snapshots", path)
                ):
                    return super().do_POST()
                self._prepare()
                try:
                    if handle_context_post(self, app, path):
                        return None
                    return self._error(404, "not_found", "not found")
                except (ValueError, TypeError) as exc:
                    return self._error(400, "invalid_request", str(exc))
                except Exception as exc:
                    return self._error(500, "internal_error", "internal server error", str(exc))

        return Handler
