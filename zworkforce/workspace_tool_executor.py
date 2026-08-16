from __future__ import annotations

import os
from pathlib import Path, PureWindowsPath
import tempfile
from typing import Any

from .tools import TOOL_DEFINITIONS, ToolError, ToolExecutor
from .workspace_grants import WorkspaceGrantError, WorkspaceGrantService

_WORKSPACE_TOOLS = {"workspace_list", "workspace_read", "workspace_write"}


def _install_workspace_id_schema() -> None:
    for name in _WORKSPACE_TOOLS:
        parameters = TOOL_DEFINITIONS[name]["schema"]["function"]["parameters"]
        properties = parameters.setdefault("properties", {})
        properties.setdefault(
            "workspace_id",
            {
                "type": "string",
                "description": "Tenant-scoped workspace grant UUID. Required in production for local file access.",
            },
        )


_install_workspace_id_schema()


class WorkspaceGrantedToolExecutor(ToolExecutor):
    """Tool executor that applies durable tenant workspace grants to file tools."""

    def __init__(self, settings, db):
        super().__init__(settings, db)
        self.grants = WorkspaceGrantService(settings, db)

    def execute(self, name: str, args: dict[str, Any], *, tenant_id: str, agent_id: str, actor: str) -> Any:
        if name not in _WORKSPACE_TOOLS:
            return super().execute(name, args, tenant_id=tenant_id, agent_id=agent_id, actor=actor)

        if name in {"workspace_list", "workspace_read"} and not self.settings.workspace_read_enabled:
            raise ToolError("workspace read tools are disabled by host policy")
        if name == "workspace_write" and not self.settings.workspace_write_enabled:
            raise ToolError("workspace write tool is disabled by host policy")

        workspace_id = str(args.get("workspace_id") or "").strip()
        try:
            if workspace_id:
                _, root = self.grants.resolve_root(
                    tenant_id,
                    workspace_id,
                    require_read=name in {"workspace_list", "workspace_read"},
                    require_write=name == "workspace_write",
                )
            elif self.settings.env == "production":
                raise WorkspaceGrantError("workspace_id grant is required for file tools in production")
            else:
                root = self.root
        except WorkspaceGrantError as exc:
            raise ToolError(str(exc)) from exc

        if name == "workspace_list":
            return self._granted_list(root, str(args.get("path", ".")))
        if name == "workspace_read":
            return self._granted_read(root, str(args.get("path", "")), int(args.get("max_bytes", 65536)))
        return self._granted_write(
            root,
            str(args.get("path", "")),
            str(args.get("content", "")),
            bool(args.get("create_parents", False)),
        )

    @staticmethod
    def _safe_path(root: Path, raw: str) -> Path:
        value = str(raw or "").strip()
        if not value or "\x00" in value or len(value) > 4096:
            raise ToolError("invalid workspace path")
        windows = PureWindowsPath(value)
        path = Path(value)
        if path.is_absolute() or windows.is_absolute() or windows.drive:
            raise ToolError("workspace path must be relative")
        try:
            target = (root / path).resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise ToolError(f"invalid workspace path: {exc}") from exc
        if target != root and root not in target.parents:
            raise ToolError("path escapes workspace grant root")
        return target

    def _granted_list(self, root: Path, raw: str) -> list[dict[str, Any]]:
        target = self._safe_path(root, raw)
        if not target.is_dir():
            raise ToolError("directory not found")
        out = []
        for item in sorted(target.iterdir(), key=lambda candidate: candidate.name)[:500]:
            try:
                resolved = item.resolve(strict=True)
                if resolved != root and root not in resolved.parents:
                    out.append({"name": item.name, "type": "blocked", "size": None})
                    continue
                stat = resolved.stat()
                out.append({
                    "name": item.name,
                    "type": "dir" if resolved.is_dir() else "file",
                    "size": stat.st_size if resolved.is_file() else None,
                })
            except (OSError, RuntimeError):
                out.append({"name": item.name, "type": "unknown", "size": None})
        return out

    def _granted_read(self, root: Path, raw: str, max_bytes: int) -> str:
        target = self._safe_path(root, raw)
        limit = max(1, min(int(max_bytes), self.settings.tool_max_output_bytes))
        if not target.is_file():
            raise ToolError("file not found")
        try:
            resolved = target.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ToolError("file could not be resolved") from exc
        if resolved != root and root not in resolved.parents:
            raise ToolError("file escapes workspace grant root")
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(resolved, flags)
        except OSError as exc:
            raise ToolError(f"file could not be opened safely: {exc}") from exc
        try:
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = -1
                data = handle.read(limit)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        return data.decode("utf-8", errors="replace")

    def _granted_write(self, root: Path, raw: str, content: str, create_parents: bool) -> dict[str, Any]:
        target = self._safe_path(root, raw)
        data = content.encode("utf-8")
        if len(data) > self.settings.workspace_write_max_bytes:
            raise ToolError("workspace write exceeds size limit")
        parent = target.parent.resolve(strict=False)
        if parent != root and root not in parent.parents:
            raise ToolError("write parent escapes workspace grant root")
        if create_parents:
            parent.mkdir(parents=True, exist_ok=True)
            parent = parent.resolve(strict=True)
            if parent != root and root not in parent.parents:
                raise ToolError("created parent escapes workspace grant root")
        if not parent.is_dir():
            raise ToolError("parent directory does not exist")
        if target.exists():
            if target.is_dir():
                raise ToolError("target path is a directory")
            try:
                resolved_target = target.resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                raise ToolError("target file could not be resolved") from exc
            if resolved_target != root and root not in resolved_target.parents:
                raise ToolError("target file escapes workspace grant root")
        fd, tmp_name = tempfile.mkstemp(prefix=".zworkforce-", dir=parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                fd = -1
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, target)
        finally:
            if fd >= 0:
                os.close(fd)
            try:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
            except OSError:
                pass
        return {"path": str(target.relative_to(root)), "bytes": len(data), "written": True}
