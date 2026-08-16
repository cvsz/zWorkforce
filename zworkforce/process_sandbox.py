from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Callable, Sequence


class ProcessSandboxError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProcessSandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    backend: str
    network_policy: str


class BubblewrapProcessSandbox:
    """Linux process sandbox with runtime capability probing and hard resource bounds."""

    BACKEND = "bubblewrap"
    MEMORY_BYTES = 1_073_741_824
    MAX_PROCESSES = 64
    MAX_OPEN_FILES = 256
    MAX_FILE_BYTES = 16_777_216
    PROBE_TIMEOUT_SECONDS = 5

    def __init__(self, settings, *, runner: Callable = subprocess.run, bwrap: str | None = None, prlimit: str | None = None):
        self.settings = settings
        self.runner = runner
        self.bwrap = bwrap or shutil.which("bwrap") or ""
        self.prlimit = prlimit or shutil.which("prlimit") or ""
        self._probe_result: tuple[bool, str] | None = None

    @staticmethod
    def _base_environment() -> dict[str, str]:
        env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/home/zworkforce",
            "LANG": os.environ.get("LANG", "C.UTF-8"),
        }
        if os.environ.get("LC_ALL"):
            env["LC_ALL"] = os.environ["LC_ALL"]
        if os.environ.get("TZ"):
            env["TZ"] = os.environ["TZ"]
        return env

    def _system_mounts(self) -> list[str]:
        args: list[str] = ["--ro-bind", "/usr", "/usr"]
        if Path("/usr/local").exists():
            args += ["--ro-bind", "/usr/local", "/usr/local"]
        for source, destination in (("usr/bin", "/bin"), ("usr/sbin", "/sbin"), ("usr/lib", "/lib"), ("usr/lib64", "/lib64")):
            target = Path("/") / source
            if target.exists():
                args += ["--symlink", source, destination]
        for path in ("/etc/passwd", "/etc/group", "/etc/nsswitch.conf", "/etc/gitconfig", "/etc/ssl/certs"):
            args += ["--ro-bind-try", path, path]
        return args

    def _bwrap_base(self) -> list[str]:
        if not self.bwrap:
            raise ProcessSandboxError("bubblewrap executable is unavailable")
        args = [
            self.bwrap,
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
            "--clearenv",
            "--cap-drop", "ALL",
            *self._system_mounts(),
            "--proc", "/proc",
            "--dev", "/dev",
            "--tmpfs", "/tmp",
            "--dir", "/run",
            "--dir", "/home",
            "--dir", "/home/zworkforce",
        ]
        for key, value in self._base_environment().items():
            args += ["--setenv", key, value]
        return args

    def _limit_prefix(self, cpu_seconds: int) -> list[str]:
        if not self.prlimit:
            raise ProcessSandboxError("prlimit executable is unavailable")
        cpu = max(1, int(cpu_seconds))
        return [
            self.prlimit,
            f"--cpu={cpu}",
            f"--as={self.MEMORY_BYTES}",
            f"--nproc={self.MAX_PROCESSES}",
            f"--nofile={self.MAX_OPEN_FILES}",
            f"--fsize={self.MAX_FILE_BYTES}",
            "--",
        ]

    def build_command(
        self,
        root: Path,
        argv: Sequence[str],
        *,
        network_policy: str,
        cpu_seconds: int,
        cwd_relative: str = ".",
    ) -> list[str]:
        if network_policy != "deny":
            raise ProcessSandboxError("process network_policy=allowlisted is not implemented; refusing to run")
        root = root.resolve(strict=True)
        if not root.is_dir():
            raise ProcessSandboxError("sandbox workspace root must be an existing directory")
        if not argv or not str(argv[0]).startswith("/"):
            raise ProcessSandboxError("sandbox command must use an absolute executable path")
        cwd_relative = str(cwd_relative or ".").strip()
        if cwd_relative in {"", "."}:
            sandbox_cwd = "/workspace"
        else:
            relative = Path(cwd_relative)
            if relative.is_absolute() or ".." in relative.parts:
                raise ProcessSandboxError("sandbox cwd must be relative to the workspace grant root")
            sandbox_cwd = "/workspace/" + relative.as_posix()
        return [
            *self._limit_prefix(cpu_seconds),
            *self._bwrap_base(),
            "--bind", str(root), "/workspace",
            "--chdir", sandbox_cwd,
            "--",
            *[str(item) for item in argv],
        ]

    def probe(self, *, force: bool = False) -> tuple[bool, str]:
        if self._probe_result is not None and not force:
            return self._probe_result
        if not self.bwrap or not self.prlimit:
            missing = "bubblewrap" if not self.bwrap else "prlimit"
            self._probe_result = (False, f"{missing} executable is unavailable")
            return self._probe_result
        try:
            with tempfile.TemporaryDirectory(prefix="zworkforce-sandbox-probe-") as directory:
                command = self.build_command(
                    Path(directory),
                    ["/usr/bin/true"],
                    network_policy="deny",
                    cpu_seconds=2,
                )
                completed = self.runner(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.PROBE_TIMEOUT_SECONDS,
                    shell=False,
                    env={"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"},
                    stdin=subprocess.DEVNULL,
                )
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout or "sandbox probe failed").strip().replace("\n", " ")[:500]
                self._probe_result = (False, detail)
            else:
                self._probe_result = (True, "ok")
        except (OSError, subprocess.SubprocessError, ProcessSandboxError) as exc:
            self._probe_result = (False, str(exc)[:500])
        return self._probe_result

    def run(
        self,
        root: Path,
        argv: Sequence[str],
        *,
        network_policy: str,
        timeout_seconds: int,
        cwd_relative: str = ".",
        stdin_text: str | None = None,
    ) -> ProcessSandboxResult:
        available, reason = self.probe()
        if not available:
            raise ProcessSandboxError(f"process sandbox backend is unavailable: {reason}")
        command = self.build_command(
            root,
            argv,
            network_policy=network_policy,
            cpu_seconds=timeout_seconds,
            cwd_relative=cwd_relative,
        )
        try:
            completed = self.runner(
                command,
                input=stdin_text,
                capture_output=True,
                text=True,
                timeout=max(1, int(timeout_seconds)),
                shell=False,
                env={"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"},
                stdin=None if stdin_text is not None else subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProcessSandboxError(f"sandboxed process timed out after {timeout_seconds}s") from exc
        except OSError as exc:
            raise ProcessSandboxError(f"sandboxed process could not start: {exc}") from exc
        limit = self.settings.tool_max_output_bytes
        return ProcessSandboxResult(
            exit_code=int(completed.returncode),
            stdout=str(completed.stdout or "")[-limit:],
            stderr=str(completed.stderr or "")[-limit:],
            backend=self.BACKEND,
            network_policy=network_policy,
        )
