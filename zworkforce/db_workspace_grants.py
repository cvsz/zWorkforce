from __future__ import annotations

import uuid
from typing import Any

from .db_base import json_dumps, json_loads, utcnow


class WorkspaceGrantMixin:
    def upsert_workspace_grant(self, tenant_id: str, grant: dict[str, Any], actor: str) -> dict[str, Any]:
        grant_id = str(grant.get("id") or uuid.uuid4())
        try:
            uuid.UUID(grant_id)
        except ValueError as exc:
            raise ValueError("workspace grant id must be a UUID") from exc
        name = str(grant.get("name") or "").strip()
        root_rel = str(grant.get("root_rel") or "").strip()
        commands = [str(item) for item in (grant.get("commands") or [])]
        network_policy = str(grant.get("network_policy") or "deny")
        expires_at = str(grant.get("expires_at") or "").strip()
        if not name or len(name) > 200:
            raise ValueError("workspace grant name is required and must be <= 200 characters")
        if not root_rel or len(root_rel) > 1024:
            raise ValueError("workspace grant root_rel is required and must be <= 1024 characters")
        if len(commands) > 32 or any(not item or len(item) > 128 for item in commands):
            raise ValueError("workspace grant commands must contain at most 32 bounded names")
        if len(set(commands)) != len(commands):
            raise ValueError("workspace grant commands must not contain duplicates")
        if network_policy not in {"deny", "allowlisted"}:
            raise ValueError("workspace grant network_policy must be deny or allowlisted")
        if not expires_at:
            raise ValueError("workspace grant expires_at is required")
        now = utcnow()
        with self.connection() as c:
            c.execute(
                """INSERT INTO workspace_grants6(
                    tenant_id,id,name,root_rel,read_enabled,write_enabled,commands_json,network_policy,
                    enabled,expires_at,created_by,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(tenant_id,id) DO UPDATE SET
                    name=excluded.name,root_rel=excluded.root_rel,read_enabled=excluded.read_enabled,
                    write_enabled=excluded.write_enabled,commands_json=excluded.commands_json,
                    network_policy=excluded.network_policy,enabled=excluded.enabled,
                    expires_at=excluded.expires_at,updated_at=excluded.updated_at""",
                (
                    tenant_id,
                    grant_id,
                    name,
                    root_rel,
                    int(bool(grant.get("read", True))),
                    int(bool(grant.get("write", False))),
                    json_dumps(commands),
                    network_policy,
                    int(bool(grant.get("enabled", True))),
                    expires_at,
                    actor,
                    now,
                    now,
                ),
            )
        result = self.get_workspace_grant(tenant_id, grant_id)
        if not result:
            raise RuntimeError("workspace grant could not be stored")
        return result

    @staticmethod
    def _decode_workspace_grant(row: Any) -> dict[str, Any]:
        result = dict(row)
        result["commands"] = json_loads(result.pop("commands_json", "[]"), [])
        result["read"] = bool(result.pop("read_enabled", 0))
        result["write"] = bool(result.pop("write_enabled", 0))
        result["enabled"] = bool(result.get("enabled"))
        return result

    def get_workspace_grant(self, tenant_id: str, grant_id: str) -> dict[str, Any] | None:
        with self.connection() as c:
            row = c.execute(
                "SELECT * FROM workspace_grants6 WHERE tenant_id=? AND id=?",
                (tenant_id, grant_id),
            ).fetchone()
        return self._decode_workspace_grant(row) if row else None

    def list_workspace_grants(self, tenant_id: str, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(int(limit), 500))
        bounded_offset = max(0, int(offset))
        with self.connection() as c:
            rows = c.execute(
                "SELECT * FROM workspace_grants6 WHERE tenant_id=? ORDER BY enabled DESC,updated_at DESC,id LIMIT ? OFFSET ?",
                (tenant_id, bounded_limit, bounded_offset),
            ).fetchall()
        return [self._decode_workspace_grant(row) for row in rows]

    def disable_workspace_grant(self, tenant_id: str, grant_id: str) -> bool:
        with self.connection() as c:
            return bool(
                c.execute(
                    "UPDATE workspace_grants6 SET enabled=0,updated_at=? WHERE tenant_id=? AND id=? AND enabled=1",
                    (utcnow(), tenant_id, grant_id),
                ).rowcount
            )
