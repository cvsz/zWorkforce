from __future__ import annotations

import base64
import os
import re

from .browser_effect_api import BrowserEffectApp

_ARTIFACT_CONTENT = re.compile(r"/api/v1/artifacts/([0-9A-Fa-f-]{36})/content")
_DEFAULT_MAX_BYTES = 8 * 1024 * 1024


class ArtifactContentApp(BrowserEffectApp):
    """Deliver tenant-scoped artifact bytes only through authenticated API authority."""

    def handler(self):
        app = self
        ParentHandler = super().handler()

        class Handler(ParentHandler):
            def _get_api(self, path: str):
                match = _ARTIFACT_CONTENT.fullmatch(path)
                if not match:
                    return super()._get_api(path)
                ctx, response = self._principal("operator", "task:write")
                if response:
                    return response
                principal, tenant_id = ctx
                artifact = app.db.get_artifact(tenant_id, match.group(1))
                if not artifact:
                    return self._error(404, "artifact_not_found", "artifact not found")
                configured = int(os.getenv("ZWORKFORCE_BROWSER_UPLOAD_MAX_BYTES", str(_DEFAULT_MAX_BYTES)))
                max_bytes = max(1, min(configured, 16 * 1024 * 1024))
                size = int(artifact.get("size_bytes") or 0)
                if size < 0 or size > max_bytes:
                    return self._error(413, "artifact_too_large", "artifact exceeds browser upload size limit")
                data = app.artifacts.read_bytes(
                    str(artifact.get("storage_uri") or ""),
                    str(artifact.get("sha256") or ""),
                )
                if len(data) != size or len(data) > max_bytes:
                    return self._error(409, "artifact_integrity_error", "artifact size does not match durable metadata")
                app.db.audit(
                    tenant_id,
                    principal.name,
                    "browser.artifact.read",
                    "artifact",
                    artifact["id"],
                    {"sha256": artifact.get("sha256", ""), "size_bytes": len(data)},
                )
                return self._json(
                    200,
                    {
                        "id": artifact["id"],
                        "name": str(artifact.get("name") or "upload.bin")[:255],
                        "content_type": str(artifact.get("content_type") or "application/octet-stream")[:255],
                        "sha256": str(artifact.get("sha256") or ""),
                        "size_bytes": len(data),
                        "content_base64": base64.b64encode(data).decode("ascii"),
                    },
                )

        return Handler
