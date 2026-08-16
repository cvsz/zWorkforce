from __future__ import annotations

import re

from .workspace_command_api import WorkspaceCommandApp
from .workspace_evidence import build_task_evidence_sidecar

_TASK_SIDECAR = re.compile(r"/api/v1/tasks/([0-9A-Fa-f-]{36})/sidecar")


class WorkspaceEvidenceApp(WorkspaceCommandApp):
    """Workspace API composition with read-only durable task evidence projection."""

    def handler(self):
        app = self
        ParentHandler = super().handler()

        class Handler(ParentHandler):
            def _get_api(self, path: str):
                match = _TASK_SIDECAR.fullmatch(path)
                if not match:
                    return super()._get_api(path)
                ctx, response = self._principal("viewer", "workforce:read")
                if response:
                    return response
                _, tenant_id = ctx
                payload = build_task_evidence_sidecar(app.db, tenant_id, match.group(1))
                if payload is None:
                    return self._error(404, "task_not_found", "task not found")
                return self._json(200, payload)

        return Handler
