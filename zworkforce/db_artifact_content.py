from __future__ import annotations

from typing import Any


class ArtifactContentMixin:
    """Tenant-scoped lookup used by governed artifact-content delivery."""

    def get_artifact(self, tenant_id: str, artifact_id: str) -> dict[str, Any] | None:
        with self.connection() as c:
            row = c.execute(
                "SELECT * FROM artifacts3 WHERE tenant_id=? AND id=?",
                (tenant_id, str(artifact_id)),
            ).fetchone()
        return self._decode(dict(row)) if row else None
