from __future__ import annotations

import re
import urllib.parse

from .workspace_evidence_api import WorkspaceEvidenceApp
from .workspace_grants import WorkspaceGrantError, WorkspaceGrantService

_GRANTS_PATH = "/api/v1/workspaces/grants"
_GRANT_DISABLE = re.compile(r"/api/v1/workspaces/grants/([0-9A-Fa-f-]{36})/disable")


class WorkspaceGrantApp(WorkspaceEvidenceApp):
    """Workspace API composition with operator-managed local workspace grants."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace_grants = WorkspaceGrantService(self.settings, self.db)

    def handler(self):
        app = self
        ParentHandler = super().handler()

        class Handler(ParentHandler):
            def _get_api(self, path: str):
                if path != _GRANTS_PATH:
                    return super()._get_api(path)
                ctx, response = self._principal("admin", "workspace:grant")
                if response:
                    return response
                _, tenant_id = ctx
                q = self._query()
                try:
                    limit = int((q.get("limit") or ["100"])[0])
                    offset = int((q.get("offset") or ["0"])[0])
                except ValueError as exc:
                    raise ValueError("limit and offset must be integers") from exc
                return self._json(200, {"items": app.db.list_workspace_grants(tenant_id, limit, offset)})

            def do_POST(self):
                path = urllib.parse.urlsplit(self.path).path
                disable = _GRANT_DISABLE.fullmatch(path)
                if path != _GRANTS_PATH and not disable:
                    return super().do_POST()
                self._prepare()
                try:
                    ctx, response = self._principal("admin", "workspace:grant")
                    if response:
                        return response
                    principal, tenant_id = ctx
                    if disable:
                        grant_id = disable.group(1)
                        existing = app.db.get_workspace_grant(tenant_id, grant_id)
                        if not existing:
                            return self._error(404, "workspace_grant_not_found", "workspace grant not found")
                        changed = app.db.disable_workspace_grant(tenant_id, grant_id)
                        app.db.audit(
                            tenant_id,
                            principal.name,
                            "workspace.grant.disable",
                            "workspace_grant",
                            grant_id,
                            {"changed": changed, "root": existing["root_rel"]},
                        )
                        return self._json(200, {"ok": True, "id": grant_id, "disabled": True})

                    body = self._body()
                    normalized = app.workspace_grants.normalize(body)
                    grant = app.db.upsert_workspace_grant(tenant_id, normalized, principal.name)
                    app.db.audit(
                        tenant_id,
                        principal.name,
                        "workspace.grant.upsert",
                        "workspace_grant",
                        grant["id"],
                        {
                            "root": grant["root_rel"],
                            "read": grant["read"],
                            "write": grant["write"],
                            "commands": grant["commands"],
                            "network_policy": grant["network_policy"],
                            "enabled": grant["enabled"],
                            "expires_at": grant["expires_at"],
                        },
                    )
                    return self._json(201, grant)
                except (WorkspaceGrantError, ValueError, TypeError) as exc:
                    return self._error(400, "invalid_request", str(exc))
                except Exception as exc:
                    return self._error(500, "internal_error", "internal server error", str(exc))

        return Handler
