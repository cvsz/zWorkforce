from dataclasses import replace
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.common import stack
from zworkforce.process_sandbox import BubblewrapProcessSandbox, ProcessSandboxError


class Completed:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class ProcessSandboxTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()

    def tearDown(self):
        self.engine.shutdown()
        self.temp.cleanup()

    def test_command_uses_namespaces_resource_limits_and_no_shared_network(self):
        sandbox = BubblewrapProcessSandbox(
            self.settings,
            bwrap="/usr/bin/bwrap",
            prlimit="/usr/bin/prlimit",
        )
        root = self.settings.workspace_root / "sandbox-root"
        root.mkdir()
        command = sandbox.build_command(
            root,
            ["/usr/bin/python3", "-c", "print('ok')"],
            network_policy="deny",
            cpu_seconds=7,
            cwd_relative=".",
        )
        self.assertEqual(command[0], "/usr/bin/prlimit")
        self.assertIn("--cpu=7", command)
        self.assertIn(f"--as={sandbox.MEMORY_BYTES}", command)
        self.assertIn(f"--nproc={sandbox.MAX_PROCESSES}", command)
        self.assertIn(f"--nofile={sandbox.MAX_OPEN_FILES}", command)
        self.assertIn(f"--fsize={sandbox.MAX_FILE_BYTES}", command)
        self.assertIn("--unshare-all", command)
        self.assertNotIn("--share-net", command)
        self.assertIn("--clearenv", command)
        self.assertIn("--new-session", command)
        self.assertIn("--die-with-parent", command)
        self.assertIn("--cap-drop", command)
        bind_index = command.index("--bind")
        self.assertEqual(command[bind_index + 1], str(root.resolve()))
        self.assertEqual(command[bind_index + 2], "/workspace")
        chdir_index = command.index("--chdir")
        self.assertEqual(command[chdir_index + 1], "/workspace")
        self.assertEqual(command[-3:], ["/usr/bin/python3", "-c", "print('ok')"])

    def test_allowlisted_network_fails_closed(self):
        sandbox = BubblewrapProcessSandbox(self.settings, bwrap="/usr/bin/bwrap", prlimit="/usr/bin/prlimit")
        root = self.settings.workspace_root / "sandbox-root"
        root.mkdir()
        with self.assertRaisesRegex(ProcessSandboxError, "allowlisted is not implemented"):
            sandbox.build_command(root, ["/usr/bin/true"], network_policy="allowlisted", cpu_seconds=1)

    def test_probe_failure_is_cached_and_run_fails_closed(self):
        calls = []

        def failing_runner(*args, **kwargs):
            calls.append((args, kwargs))
            return Completed(returncode=1, stderr="Creating new namespace failed")

        sandbox = BubblewrapProcessSandbox(
            self.settings,
            runner=failing_runner,
            bwrap="/usr/bin/bwrap",
            prlimit="/usr/bin/prlimit",
        )
        available, reason = sandbox.probe()
        self.assertFalse(available)
        self.assertIn("namespace", reason)
        again = sandbox.probe()
        self.assertEqual(again, (available, reason))
        self.assertEqual(len(calls), 1)

        root = self.settings.workspace_root / "sandbox-root"
        root.mkdir()
        with self.assertRaisesRegex(ProcessSandboxError, "backend is unavailable"):
            sandbox.run(root, ["/usr/bin/true"], network_policy="deny", timeout_seconds=1)
        self.assertEqual(len(calls), 1)

    def test_successful_run_is_bounded_and_marks_backend(self):
        calls = []

        def successful_runner(command, **kwargs):
            calls.append((command, kwargs))
            if command[-1] == "/usr/bin/true":
                return Completed(returncode=0)
            return Completed(returncode=0, stdout="x" * (self.settings.tool_max_output_bytes + 50), stderr="err")

        sandbox = BubblewrapProcessSandbox(
            self.settings,
            runner=successful_runner,
            bwrap="/usr/bin/bwrap",
            prlimit="/usr/bin/prlimit",
        )
        root = self.settings.workspace_root / "sandbox-root"
        root.mkdir()
        result = sandbox.run(
            root,
            ["/usr/bin/python3", "-c", "print('ok')"],
            network_policy="deny",
            timeout_seconds=3,
            stdin_text="payload",
        )
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.backend, "bubblewrap")
        self.assertEqual(result.network_policy, "deny")
        self.assertEqual(len(result.stdout), self.settings.tool_max_output_bytes)
        self.assertEqual(len(calls), 2)
        self.assertFalse(calls[0][1]["shell"])
        self.assertFalse(calls[1][1]["shell"])
        self.assertEqual(calls[1][1]["input"], "payload")


if __name__ == "__main__":
    unittest.main()
