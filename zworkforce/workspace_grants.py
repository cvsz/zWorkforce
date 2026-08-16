from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

MAX_GRANT_DAYS = 365


class WorkspaceGrantError(ValueError):
    pass


def _aware_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise WorkspaceGrantError("expires_at must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise WorkspaceGrantError("expires_at must include a timezone offset")
    return parsed.astimezone(timezone.utc)


class WorkspaceGrantService:
    """Validate operator workspace grants against the configured host workspace ceiling."""

    def __init__(self, settings, db):
        self.settings = settings
        self.db = db
        self.host_root = Path(settings.workspace_root).expanduser().resolve()

    def normalize_root(self, raw: str) -> str:
        value = str(raw or "").strip()
        if not value or "\x00" in value or len(value) > 1024:
            raise WorkspaceGrantError("workspace grant root is invalid")
        posix = Path(value)
        windows = PureWindowsPath(value)
        if posix.is_absolute() or windows.is_absolute() or windows.drive:
            raise WorkspaceGrantError("workspace grant root must be relative to the configured workspace root")
        try:
            candidate = (self.host_root / posix).resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise WorkspaceGrantError("workspace grant root must resolve to an existing directory") from exc
        if candidate != self.host_root and self.host_root not in candidate.parents:
            raise WorkspaceGrantError("workspace grant root escapes the configured workspace root")
        if not candidate.is_dir():
            raise WorkspaceGrantError("workspace grant root must be a directory")
        relative = candidate.relative_to(self.host_root)
        return "." if not relative.parts else relative.as_posix()

    def validate_expiry(self, value: str) -> str:
        expires = _aware_datetime(str(value or "").strip())
        now = datetime.now(timezone.utc)
        if expires <= now:
            raise WorkspaceGrantError("workspace grant expires_at must be in the future")
        if expires > now + timedelta(days=MAX_GRANT_DAYS):
            raise WorkspaceGrantError(f"workspace grant expires_at must be within {MAX_GRANT_DAYS} days")
        return expires.isoformat(timespec="seconds")

    def normalize(self, body: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(body, dict):
            raise WorkspaceGrantError("workspace grant request must be an object")
        commands = body.get("commands") or []
        if not isinstance(commands, list) or any(not isinstance(item, str) for item in commands):
            raise WorkspaceGrantError("commands must be an array of command names")
        commands = [item.strip() for item in commands if item.strip()]
        unknown = sorted(set(commands) - set(self.settings.shell_allowlist))
        if unknown:
            raise WorkspaceGrantError("commands contain executables outside the configured shell allowlist")
        read = body.get("read", True)
        write = body.get("write", False)
        if not isinstance(read, bool) or not isinstance(write, bool):
            raise WorkspaceGrantError("read and write must be booleans")
        network_policy = str(body.get("network_policy") or "deny").strip().lower()
        if network_policy not in {"deny", "allowlisted"}:
            raise WorkspaceGrantError("network_policy must be deny or allowlisted")
        return {
            "id": body.get("id"),
            "name": str(body.get("name") or "").strip(),
            "root_rel": self.normalize_root(str(body.get("root") or "")),
            "read": read,
            "write": write,
            "commands": commands,
            "network_policy": network_policy,
            "enabled": bool(body.get("enabled", True)),
            "expires_at": self.validate_expiry(str(body.get("expires_at") or "")),
        }

    def resolve_root(self, tenant_id: str, grant_id: str, *, require_read: bool = False, require_write: bool = False) -> tuple[dict[str, Any], Path]:
        grant = self.db.get_workspace_grant(tenant_id, grant_id)
        if not grant or not grant.get("enabled"):
            raise WorkspaceGrantError("workspace grant not found or disabled")
        expires = _aware_datetime(str(grant.get("expires_at") or ""))
        if expires <= datetime.now(timezone.utc):
            raise WorkspaceGrantError("workspace grant has expired")
        if require_read and not grant.get("read"):
            raise WorkspaceGrantError("workspace grant does not allow reads")
        if require_write and not grant.get("write"):
            raise WorkspaceGrantError("workspace grant does not allow writes")
        relative = str(grant.get("root_rel") or "")
        # Re-resolve on every use so a symlink/junction changed after grant creation cannot escape the host ceiling.
        root_rel = self.normalize_root(relative)
        if root_rel != relative:
            raise WorkspaceGrantError("workspace grant root no longer resolves to its approved canonical path")
        root = self.host_root if relative == "." else (self.host_root / relative).resolve(strict=True)
        return grant, root
