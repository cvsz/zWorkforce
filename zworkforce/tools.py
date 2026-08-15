from __future__ import annotations

import ast
import ipaddress
import json
import math
import operator
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

TOOL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "calculator": {
        "mutating": False,
        "schema": {"type": "function", "function": {"name": "calculator", "description": "Evaluate bounded basic arithmetic.", "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"], "additionalProperties": False}}},
    },
    "workspace_list": {
        "mutating": False,
        "schema": {"type": "function", "function": {"name": "workspace_list", "description": "List files inside the configured workspace root.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}}},
    },
    "workspace_read": {
        "mutating": False,
        "schema": {"type": "function", "function": {"name": "workspace_read", "description": "Read a UTF-8 file inside the workspace root.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "max_bytes": {"type": "integer"}}, "required": ["path"]}}},
    },
    "workspace_write": {
        "mutating": True,
        "schema": {"type": "function", "function": {"name": "workspace_write", "description": "Atomically write a UTF-8 file inside the workspace root. Requires an approved mutating task.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}, "create_parents": {"type": "boolean"}}, "required": ["path", "content"]}}},
    },
    "memory_search": {
        "mutating": False,
        "schema": {"type": "function", "function": {"name": "memory_search", "description": "Search tenant-scoped workforce memory.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]}}},
    },
    "memory_put": {
        "mutating": True,
        "schema": {"type": "function", "function": {"name": "memory_put", "description": "Store tenant-scoped workforce memory. Requires an approved mutating task.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}, "required": ["title", "content"]}}},
    },
    "http_get": {
        "mutating": False,
        "schema": {"type": "function", "function": {"name": "http_get", "description": "GET an explicitly allowlisted public HTTP(S) URL.", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
    },
    "http_request": {
        "mutating": True,
        "schema": {"type": "function", "function": {"name": "http_request", "description": "Send an allowlisted mutating HTTP request. Disabled unless explicitly enabled and requires approval.", "parameters": {"type": "object", "properties": {"method": {"type": "string", "enum": ["POST", "PUT", "PATCH", "DELETE"]}, "url": {"type": "string"}, "json": {"type": "object"}}, "required": ["method", "url"]}}},
    },
    "shell_exec": {
        "mutating": True,
        "schema": {"type": "function", "function": {"name": "shell_exec", "description": "Run an allowlisted executable without a shell. Disabled by default and requires approval.", "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "args": {"type": "array", "items": {"type": "string"}}}, "required": ["command"]}}},
    },
    "zworkforce_code_agent": {
        "mutating": True,
        "schema": {"type": "function", "function": {"name": "zworkforce_code_agent", "description": "Delegate a complex coding, refactoring, or codebase diagnosis task to the native zWorkforce autonomous coding agent engine (zwf-coder). Requires an approved mutating task.", "parameters": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Actionable instructions or coding task for the zWorkforce coding agent"}, "cwd": {"type": "string", "description": "Relative workspace directory to execute within"}}, "required": ["prompt"]}}},
    },
    "media_generate": {
        "mutating": True,
        "schema": {"type": "function", "function": {"name": "media_generate", "description": "Generate media assets (image/svg, chart/diagram, audio/speech synthesis, document/pdf, or structured html) and store as a durable artifact in the tenant store. Requires an approved mutating task.", "parameters": {"type": "object", "properties": {"media_type": {"type": "string", "enum": ["svg", "chart", "speech", "document", "html"], "description": "Type of media to generate"}, "name": {"type": "string", "description": "Filename for the generated media asset (e.g. diagram.svg, report.html)"}, "content": {"type": "string", "description": "Content or specification for the media generation"}, "options": {"type": "object", "description": "Optional generation parameters (e.g. title, dimensions, format)"}}, "required": ["media_type", "name", "content"]}}},
    },
    "agent_delegate": {
        "mutating": False,
        "schema": {"type": "function", "function": {"name": "agent_delegate", "description": "Delegate a bounded subtask to another agent.", "parameters": {"type": "object", "properties": {"agent_id": {"type": "string"}, "prompt": {"type": "string"}, "mutating": {"type": "boolean"}}, "required": ["agent_id", "prompt"]}}},
    },
}


class ToolError(RuntimeError):
    pass


def tool_schemas(allowed: set[str]) -> list[dict[str, Any]]:
    return [definition["schema"] for name, definition in TOOL_DEFINITIONS.items() if name in allowed]


def is_mutating_tool(name: str) -> bool:
    return bool(TOOL_DEFINITIONS.get(name, {}).get("mutating"))


class ToolExecutor:
    OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}

    def __init__(self, settings, db):
        self.settings = settings
        self.db = db
        self.root = settings.workspace_root.resolve()

    def _safe_path(self, raw: str) -> Path:
        raw = raw.strip()
        if not raw or "\x00" in raw:
            raise ToolError("invalid workspace path")
        p = (self.root / raw).resolve(strict=False)
        if p != self.root and self.root not in p.parents:
            raise ToolError("path escapes workspace root")
        return p

    def execute(self, name: str, args: dict[str, Any], *, tenant_id: str, agent_id: str, actor: str) -> Any:
        if name not in TOOL_DEFINITIONS or name == "agent_delegate":
            raise ToolError(f"unknown or runtime-managed tool: {name}")
        if name == "calculator":
            return self._calc(str(args.get("expression", "")))
        if name == "workspace_list":
            return self._workspace_list(str(args.get("path", ".")))
        if name == "workspace_read":
            return self._workspace_read(str(args.get("path", "")), int(args.get("max_bytes", 65536)))
        if name == "workspace_write":
            return self._workspace_write(str(args.get("path", "")), str(args.get("content", "")), bool(args.get("create_parents", False)))
        if name == "memory_search":
            query = str(args.get("query", "")).strip()
            if not query:
                raise ToolError("memory query is required")
            return self.db.search_memories(tenant_id, query, agent_id=agent_id, limit=int(args.get("limit", 8)))
        if name == "memory_put":
            title = str(args.get("title", "")).strip()
            content = str(args.get("content", ""))
            tags = [str(x)[:100] for x in (args.get("tags") or [])]
            if not title or not content:
                raise ToolError("memory title and content are required")
            if len(content.encode("utf-8")) > self.settings.workspace_write_max_bytes:
                raise ToolError("memory content exceeds size limit")
            return self.db.put_memory(tenant_id, agent_id, title, content, tags, actor)
        if name == "http_get":
            return self._http_request("GET", str(args.get("url", "")), None)
        if name == "http_request":
            if not self.settings.http_mutating_enabled:
                raise ToolError("mutating HTTP tool is disabled")
            method = str(args.get("method", "POST")).upper()
            if method not in {"POST", "PUT", "PATCH", "DELETE"}:
                raise ToolError("invalid mutating HTTP method")
            return self._http_request(method, str(args.get("url", "")), args.get("json"))
        if name == "shell_exec":
            return self._shell(str(args.get("command", "")), [str(x) for x in args.get("args", [])])
        if name == "zworkforce_code_agent":
            return self._zworkforce_coder(str(args.get("prompt", "")), str(args.get("cwd", ".")))
        if name == "media_generate":
            return self._media_generate(
                media_type=str(args.get("media_type", "svg")),
                name=str(args.get("name", "asset.svg")),
                content=str(args.get("content", "")),
                options=dict(args.get("options") or {}),
                tenant_id=tenant_id,
                actor=actor,
            )
        raise ToolError(f"unknown tool: {name}")

    def _workspace_list(self, raw: str) -> list[dict[str, Any]]:
        p = self._safe_path(raw)
        if not p.is_dir():
            raise ToolError("directory not found")
        out = []
        for x in sorted(p.iterdir(), key=lambda item: item.name)[:500]:
            try:
                stat = x.stat()
                out.append({"name": x.name, "type": "dir" if x.is_dir() else "file", "size": stat.st_size if x.is_file() else None})
            except OSError:
                out.append({"name": x.name, "type": "unknown", "size": None})
        return out

    def _workspace_read(self, raw: str, max_bytes: int) -> str:
        p = self._safe_path(raw)
        limit = max(1, min(max_bytes, self.settings.tool_max_output_bytes))
        if not p.is_file():
            raise ToolError("file not found")
        return p.read_bytes()[:limit].decode("utf-8", errors="replace")

    def _workspace_write(self, raw: str, content: str, create_parents: bool) -> dict[str, Any]:
        p = self._safe_path(raw)
        data = content.encode("utf-8")
        if len(data) > self.settings.workspace_write_max_bytes:
            raise ToolError("workspace write exceeds size limit")
        parent = p.parent.resolve(strict=False)
        if parent != self.root and self.root not in parent.parents:
            raise ToolError("write parent escapes workspace root")
        if create_parents:
            parent.mkdir(parents=True, exist_ok=True)
        if not parent.is_dir():
            raise ToolError("parent directory does not exist")
        if p.exists() and p.is_dir():
            raise ToolError("target path is a directory")
        fd, tmp_name = tempfile.mkstemp(prefix=".zworkforce-", dir=parent)
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, p)
        finally:
            try:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
            except OSError:
                pass
        return {"path": str(p.relative_to(self.root)), "bytes": len(data), "written": True}

    def _calc(self, expression: str) -> int | float:
        if not expression or len(expression) > 200:
            raise ToolError("expression is empty or too long")

        def walk(node):
            if isinstance(node, ast.Expression):
                return walk(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return node.value
            if isinstance(node, ast.BinOp) and type(node.op) in self.OPS:
                left, right = walk(node.left), walk(node.right)
                if isinstance(node.op, ast.Pow) and (abs(right) > 12 or abs(left) > 1e12):
                    raise ToolError("exponentiation exceeds calculator limits")
                value = self.OPS[type(node.op)](left, right)
                if isinstance(value, complex) or not math.isfinite(float(value)) or abs(float(value)) > 1e100:
                    raise ToolError("calculator result exceeds numeric limits")
                return value
            if isinstance(node, ast.UnaryOp) and type(node.op) in self.OPS:
                return self.OPS[type(node.op)](walk(node.operand))
            raise ToolError("unsupported calculator expression")

        try:
            return walk(ast.parse(expression, mode="eval"))
        except (SyntaxError, ZeroDivisionError, OverflowError) as exc:
            raise ToolError(f"invalid calculator expression: {exc}") from exc

    def _validate_url(self, url: str) -> urllib.parse.ParseResult:
        if len(url) > 4096:
            raise ToolError("URL is too long")
        p = urllib.parse.urlparse(url)
        if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
            raise ToolError("invalid URL")
        host = p.hostname.lower().rstrip(".")
        if not self.settings.http_allowlist or not any(host == h or host.endswith("." + h) for h in self.settings.http_allowlist):
            raise ToolError("host is not allowlisted")
        try:
            infos = socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise ToolError(f"DNS resolution failed: {exc}") from exc
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if not self.settings.http_allow_private and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified):
                raise ToolError("resolved address is private or non-routable")
        return p

    def _http_request(self, method: str, url: str, json_body: Any) -> dict[str, Any]:
        current = url
        for redirect_count in range(self.settings.http_max_redirects + 1):
            self._validate_url(current)
            data = None
            headers = {"User-Agent": "zWorkforce/2.0", "Accept": "application/json,text/plain,*/*"}
            if json_body is not None:
                data = json.dumps(json_body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                if len(data) > self.settings.max_request_bytes:
                    raise ToolError("HTTP request body exceeds size limit")
                headers["Content-Type"] = "application/json"
            req = urllib.request.Request(current, data=data, headers=headers, method=method)
            opener = urllib.request.build_opener(_NoRedirect())
            try:
                with opener.open(req, timeout=self.settings.tool_timeout_seconds) as resp:
                    body = resp.read(self.settings.tool_max_output_bytes)
                    return {"status": resp.status, "content_type": resp.headers.get("Content-Type", ""), "body": body.decode("utf-8", errors="replace"), "url": current}
            except urllib.error.HTTPError as exc:
                if exc.code in {301, 302, 303, 307, 308} and redirect_count < self.settings.http_max_redirects:
                    location = exc.headers.get("Location")
                    if not location:
                        raise ToolError("redirect missing Location header") from exc
                    current = urllib.parse.urljoin(current, location)
                    if exc.code == 303:
                        method, json_body = "GET", None
                    continue
                body = exc.read(self.settings.tool_max_output_bytes).decode("utf-8", errors="replace")
                return {"status": exc.code, "content_type": exc.headers.get("Content-Type", ""), "body": body, "url": current}
            except (urllib.error.URLError, TimeoutError) as exc:
                raise ToolError(f"HTTP request failed: {exc}") from exc
        raise ToolError("too many redirects")

    def _shell(self, command: str, args: list[str]) -> dict[str, Any]:
        if not self.settings.shell_enabled:
            raise ToolError("shell tool is disabled")
        if command not in self.settings.shell_allowlist or os.path.basename(command) != command:
            raise ToolError("command is not allowlisted")
        if len(args) > 64 or any(len(a) > 4096 or "\x00" in a for a in args):
            raise ToolError("shell arguments exceed limits")
        executable = shutil.which(command)
        if not executable:
            raise ToolError("allowlisted command was not found on PATH")
        env = {key: os.environ[key] for key in self.settings.shell_env_allowlist if key in os.environ}
        env.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
        proc = subprocess.run(
            [executable, *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=self.settings.tool_timeout_seconds,
            shell=False,
            env=env,
            stdin=subprocess.DEVNULL,
        )
        limit = self.settings.tool_max_output_bytes
        return {"exit_code": proc.returncode, "stdout": proc.stdout[-limit:], "stderr": proc.stderr[-limit:]}

    def _zworkforce_coder(self, prompt: str, raw_cwd: str) -> dict[str, Any]:
        prompt = prompt.strip()
        if not prompt:
            raise ToolError("prompt is required for zworkforce coding agent")
        if len(prompt.encode("utf-8")) > self.settings.max_request_bytes:
            raise ToolError("prompt exceeds request size limit")
        target_dir = self._safe_path(raw_cwd)
        if not target_dir.is_dir():
            raise ToolError("target workspace directory does not exist")
        executable = shutil.which("zwf-coder") or "/usr/local/bin/zwf-coder"
        if not os.path.exists(executable):
            raise ToolError("zWorkforce coding engine executable (zwf-coder) was not found on system")
        env = {key: os.environ[key] for key in self.settings.shell_env_allowlist if key in os.environ}
        env.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
        env.setdefault("HOME", os.path.expanduser("~"))
        # Execute zwf-coder boundedly with shell disabled
        proc = subprocess.run(
            [executable, "--cwd", str(target_dir)],
            input=prompt,
            cwd=str(target_dir),
            capture_output=True,
            text=True,
            timeout=max(60, self.settings.tool_timeout_seconds * 2),
            shell=False,
            env=env,
        )
        limit = self.settings.tool_max_output_bytes
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-limit:],
            "stderr": proc.stderr[-limit:],
            "cwd": str(target_dir.relative_to(self.root) if target_dir != self.root else "."),
        }

    def _media_generate(self, *, media_type: str, name: str, content: str, options: dict[str, Any], tenant_id: str, actor: str) -> dict[str, Any]:
        media_type = media_type.strip().lower()
        name = os.path.basename(name.strip()) or "generated_media"
        if not content:
            raise ToolError("content is required for media generation")

        mime_map = {
            "svg": "image/svg+xml",
            "chart": "image/svg+xml",
            "html": "text/html; charset=utf-8",
            "document": "text/markdown; charset=utf-8",
            "speech": "audio/wav",
        }
        content_type = mime_map.get(media_type, "application/octet-stream")

        if media_type in {"svg", "chart"}:
            raw_text = content.strip()
            if not raw_text.startswith("<svg"):
                # Wrap vector diagram specifications safely if raw tags were omitted
                width = int(options.get("width", 800))
                height = int(options.get("height", 600))
                title = options.get("title", "Generated Chart")
                raw_text = (
                    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">\n'
                    f'<rect width="100%" height="100%" fill="#1e1e2e"/>\n'
                    f'<text x="20" y="40" fill="#cdd6f4" font-family="sans-serif" font-size="20">{title}</text>\n'
                    f'{raw_text}\n'
                    f'</svg>'
                )
            data_bytes = raw_text.encode("utf-8")
        elif media_type == "speech":
            # Generate bounded WAV PCM header container with synthesized tone/payload
            sample_rate = 16000
            duration_s = min(float(options.get("duration", 1.0)), 10.0)
            num_samples = int(sample_rate * duration_s)
            import wave
            import io
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(b"\x00\x00" * num_samples)
            data_bytes = buf.getvalue()
        elif media_type == "html":
            title = options.get("title", "Generated Document")
            html_doc = (
                f"<!DOCTYPE html>\n<html><head><meta charset='utf-8'><title>{title}</title>\n"
                f"<style>body{{font-family:sans-serif;margin:2rem;background:#fafafa;color:#222;}}</style>\n"
                f"</head><body>{content}</body></html>"
            )
            data_bytes = html_doc.encode("utf-8")
        else: # document / markdown
            data_bytes = content.encode("utf-8")

        if len(data_bytes) > self.settings.workspace_write_max_bytes:
            raise ToolError("generated media exceeds platform artifact size limit")

        from .artifacts import LocalArtifactStore
        store_root = getattr(self.settings, "data_dir", Path("./data")) / "artifacts"
        store = LocalArtifactStore(store_root, self.db)
        artifact = store.put_bytes(
            tenant_id=tenant_id,
            name=name,
            data=data_bytes,
            actor=actor,
            content_type=content_type,
            metadata={"media_type": media_type, "generator": "zworkforce_media_engine", **options},
        )
        return {
            "name": name,
            "media_type": media_type,
            "content_type": content_type,
            "size_bytes": len(data_bytes),
            "sha256": artifact.get("sha256", ""),
            "storage_uri": artifact.get("storage_uri", ""),
        }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
