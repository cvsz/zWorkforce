from __future__ import annotations

import os
from pathlib import Path, PureWindowsPath
import shutil
import tempfile
from typing import Any

from .process_sandbox import BubblewrapProcessSandbox, ProcessSandboxError
from .tools import TOOL_DEFINITIONS, ToolError, ToolExecutor
from .workspace_grants import WorkspaceGrantError, WorkspaceGrantService

_FILE_TOOLS = {"workspace_list", "workspace_read", "workspace_write"}
_PROCESS_TOOLS = {"shell_exec", "zworkforce_code_agent"}
_WORKSPACE_TOOLS = _FILE_TOOLS | _PROCESS_TOOLS


def _install_workspace_id_schema() -> None:
    for name in _WORKSPACE_TOOLS:
        parameters = TOOL_DEFINITIONS[name]["schema"]["function"]["parameters"]
        properties = parameters.setdefault(
            "properties", {}
        )
        properties.setdefault(
            "workspace_id",
            {
                "type": "string",
                "description": "Tenant-scoped workspace grant UUID. Required in production for local file/process access.",
            },
        )


_install_workspace_id_schema()


class WorkspaceGrantedToolExecutor(ToolExecutor):
    """Tool executor that applies durable tenant workspace grants to local file/process tools."""

    def __init__(self, settings, db):
        super().__init__(settings, db)
        self.grants = WorkspaceGrantService(settings, db)
        self.sandbox = BubblewrapProcessSandbox(settings)

    def execute(self, name: str, args: dict[str, Any], *, tenant_id: str, agent_id: str, actor: str) -> Any:
        if name not in _WORKSPACE_TOOLS:
            return super().execute(name, args, tenant_id=tenant_id, agent_id=agent_id, actor=actor)
        if name in _FILE_TOOLS:
            return self._execute_file_tool(name, args, tenant_id=tenant_id)
        return self._execute_process_tool(name, args, tenant_id=tenant_id, agent_id=agent_id, actor=actor)

    def _execute_file_tool(self, name: str, args: dict[str, Any], *, tenant_id: str) -> Any:
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

    def _resolve_process_grant(self, tenant_id: str, args: dict[str, Any]) -> tuple[dict[str, Any], Path] | None:
        workspace_id = str(args.get("workspace_id") or "").strip()
        if not workspace_id:
            if self.settings.env == "production":
                raise ToolError("workspace_id grant is required for process tools in production")
            return None
        try:
            grant, root = self.grants.resolve_root(tenant_id, workspace_id, require_write=True)
        except WorkspaceGrantError as exc:
            raise ToolError(str(exc)) from exc
        if grant.get("network_policy") != "deny":
            raise ToolError("process network_policy=allowlisted is not implemented; refusing to run")
        return grant, root

    def _execute_process_tool(self, name: str, args: dict[str, Any], *, tenant_id: str, agent_id: str, actor: str) -> Any:
        resolved = self._resolve_process_grant(tenant_id, args)
        if resolved is None:
            # Non-production compatibility path. No sandbox claim is made for legacy calls without a grant.
            return super().execute(name, args, tenant_id=tenant_id, agent_id=agent_id, actor=actor)
        grant, root = resolved
        if name == "shell_exec":
            raw_args = args.get("args", [])
            if not isinstance(raw_args, list) or any(not isinstance(item, (str, int, float, bool)) for item in raw_args):
                raise ToolError("shell args must be an array of scalar values")
            return self._sandboxed_shell(grant, root, str(args.get("command", "")), [str(item) for item in raw_args])
        return self._sandboxed_coder(grant, root, str(args.get("prompt", "")), str(args.get("cwd", ".")))

    def _sandboxed_shell(self, grant: dict[str, Any], root: Path, command: str, args: list[str]) -> dict[str, Any]:
        if not self.settings.shell_enabled:
            raise ToolError("shell tool is disabled")
        if command not in self.settings.shell_allowlist or os.path.basename(command) != command:
            raise ToolError("command is not allowlisted by host policy")
        if command not in set(grant.get("commands") or []):
            raise ToolError("command is not allowlisted by workspace grant")
        if len(args) > 64 or any(len(item) > 4096 or "\x00" in item for item in args):
            raise ToolError("shell arguments exceed limits")
        executable = shutil.which(command)
        if not executable or not os.path.isabs(executable):
            raise ToolError("allowlisted command was not found on PATH")
        try:
            result = self.sandbox.run(
                root,
                [executable, *args],
                network_policy=str(grant["network_policy"]),
                timeout_seconds=self.settings.tool_timeout_seconds,
            )
        except ProcessSandboxError as exc:
            raise ToolError(str(exc)) from exc
        return {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "sandbox_backend": result.backend,
            "network_policy": result.network_policy,
        }

    def _sandboxed_coder(self, grant: dict[str, Any], root: Path, prompt: str, raw_cwd: str) -> dict[str, Any]:
        prompt = prompt.strip()
        if not prompt:
            raise ToolError("prompt is required for zworkforce coding agent")
        if len(prompt.encode("utf-8")) > self.settings.max_request_bytes:
            raise ToolError("prompt exceeds request size limit")
        target_dir = self._safe_path_for_root(root, raw_cwd)
        if not target_dir.is_dir():
            raise ToolError("target workspace directory does not exist")
        executable = shutil.which("zktcoder") or shutil.which("zwf-coder") or "/usr/local/bin/zwf-coder"
        if not os.path.exists(executable) or not os.path.isabs(executable):
            raise ToolError("zWorkforce coding engine executable (zwf-coder) was not found on system")
        relative = "." if target_dir == root else target_dir.relative_to(root).as_posix()
        sandbox_cwd = "/workspace" if relative == "." else f"/workspace/{relative}"
        try:
            result = self.sandbox.run(
                root,
                [executable, "--cwd", sandbox_cwd],
                network_policy=str(grant["network_policy"]),
                timeout_seconds=max(60, self.settings.tool_timeout_seconds * 2),
                cwd_relative=relative,
                stdin_text=prompt,
            )
        except ProcessSandboxError as exc:
            raise ToolError(str(exc)) from exc
        return {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": relative,
            "sandbox_backend": result.backend,
            "network_policy": result.network_policy,
        }

    @staticmethod
    def _safe_path_for_root(root: Path, raw: str) -> Path:
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
        target = self._safe_path_for_root(root, raw)
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
        target = self._safe_path_for_root(root, raw)
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
        target = self._safe_path_for_root(root, raw)
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
