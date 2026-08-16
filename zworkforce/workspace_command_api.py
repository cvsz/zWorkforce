from __future__ import annotations

import urllib.parse

from .workspace_commands import list_workspace_commands, parse_workspace_command
from .workspace_context_api import WorkspaceContextApp

_COMMANDS_PATH = "/api/v1/workspaces/commands"
_RESOLVE_PATH = "/api/v1/workspaces/commands/resolve"


def _principal(handler, role: str, scope: str):
    ctx, response = handler._principal(role, scope)
    if response:
        return None
    return ctx


def _command_payload(app, principal, command, argument: str = "") -> dict:
    payload = command.public()
    payload["available"] = app.auth.require(principal, command.role, command.scope)
    if argument:
        payload["argument"] = argument
    return payload


class WorkspaceCommandApp(WorkspaceContextApp):
    """Workspace/context API plus server-authorized slash-command discovery and resolution."""

    def handler(self):
        app = self
        ParentHandler = super().handler()

        class Handler(ParentHandler):
            def _get_api(self, path: str):
                if path != _COMMANDS_PATH:
                    return super()._get_api(path)
                ctx = _principal(self, "viewer", "workspace:read")
                if ctx is None:
                    return None
                principal, _ = ctx
                return self._json(
                    200,
                    {"items": [_command_payload(app, principal, item) for item in list_workspace_commands()]},
                )

            def do_POST(self):
                path = urllib.parse.urlsplit(self.path).path
                if path != _RESOLVE_PATH:
                    return super().do_POST()
                self._prepare()
                try:
                    ctx = _principal(self, "viewer", "workspace:read")
                    if ctx is None:
                        return None
                    principal, tenant_id = ctx
                    body = self._body()
                    command, argument = parse_workspace_command(str(body.get("text", "")))
                    if not app.auth.require(principal, command.role, command.scope):
                        return self._error(
                            403,
                            "workspace_command_not_authorized",
                            "command role or scope requirement failed",
                        )
                    result = _command_payload(app, principal, command, argument)
                    result["tenant_id"] = tenant_id
                    result["resolved"] = True
                    return self._json(200, result)
                except (ValueError, TypeError) as exc:
                    return self._error(400, "invalid_request", str(exc))
                except Exception as exc:
                    return self._error(500, "internal_error", "internal server error", str(exc))

        return Handler
