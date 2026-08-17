from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from tests.common import stack
from zworkforce.policy import PolicyEngine
from zworkforce.process_sandbox import ProcessSandboxError, ProcessSandboxResult
from zworkforce.tools import tool_schemas


class FakeSandbox:
    def __init__(self, *, fail: str = ""):
        self.fail = fail
        self.calls = []

    def run(self, root, argv, **kwargs):
        self.calls.append((Path(root), list(argv), dict(kwargs)))
        if self.fail:
            raise ProcessSandboxError(self.fail)
        return ProcessSandboxResult(0, "sandbox-stdout", "", "bubblewrap", kwargs["network_policy"])


class WorkspaceProcessSandboxTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.dev_engine, self.auth = stack()
        self.project = self.settings.workspace_root / "process-project"
        self.project.mkdir(parents=True)
        (self.project / "subdir").mkdir()
        self.engines = []

    def tearDown(self):
        self.dev_engine.shutdown()
        for engine in self.engines:
            engine.shutdown()
        self.temp.cleanup()

    @staticmethod
    def future():
        return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(timespec="seconds")

    def make_engine(self, *, shell_enabled=True):
        settings = replace(self.settings, env="production", embedded_workers=0, shell_enabled=shell_enabled)
        engine = PolicyEngine(settings, self.db, self.provider)
        self.engines.append(engine)
        return engine

    def grant(self, *, write=True, commands=None, network_policy="deny", tenant_id="default"):
        return self.db.upsert_workspace_grant(
            tenant_id,
            {
                "name": "Process sandbox grant",
                "root_rel": "process-project",
                "read": True,
                "write": write,
                "commands": list(commands or []),
                "network_policy": network_policy,
                "enabled": True,
                "expires_at": self.future(),
            },
            "test",
        )

    def test_process_tool_schemas_expose_workspace_id(self):
        schemas = {item["function"]["name"]: item for item in tool_schemas({"shell_exec", "zworkforce_code_agent"})}
        self.assertEqual(set(schemas), {"shell_exec", "zworkforce_code_agent"})
        for item in schemas.values():
            self.assertIn("workspace_id", item["function"]["parameters"]["properties"])

    def test_production_process_tools_require_workspace_grant(self):
        engine = self.make_engine()
        for name, args in (
            ("shell_exec", {"command": "python", "args": ["-V"]}),
            ("zworkforce_code_agent", {"prompt": "inspect project", "cwd": "."}),
        ):
            with self.subTest(name=name):
                with self.assertRaisesRegex(Exception, "workspace_id grant is required"):
                    engine.tools.execute(name, args, tenant_id="default", agent_id="software-engineer", actor="test")

    def test_shell_requires_write_grant_and_command_membership(self):
        engine = self.make_engine()
        fake = FakeSandbox()
        engine.tools.sandbox = fake
        readonly = self.grant(write=False, commands=["python"])
        with self.assertRaisesRegex(Exception, "does not allow writes"):
            engine.tools.execute(
                "shell_exec", {"workspace_id": readonly["id"], "command": "python", "args": ["-V"]},
                tenant_id="default", agent_id="software-engineer", actor="test",
            )

        grant = self.grant(write=True, commands=["git"])
        with self.assertRaisesRegex(Exception, "workspace grant"):
            engine.tools.execute(
                "shell_exec", {"workspace_id": grant["id"], "command": "python", "args": ["-V"]},
                tenant_id="default", agent_id="software-engineer", actor="test",
            )
        self.assertEqual(fake.calls, [])

    def test_shell_uses_probed_sandbox_with_grant_root(self):
        engine = self.make_engine()
        fake = FakeSandbox()
        engine.tools.sandbox = fake
        grant = self.grant(write=True, commands=["python"])
        with patch("zworkforce.workspace_tool_executor.shutil.which", return_value="/usr/bin/python3"):
            result = engine.tools.execute(
                "shell_exec",
                {"workspace_id": grant["id"], "command": "python", "args": ["-c", "print('ok')"]},
                tenant_id="default", agent_id="software-engineer", actor="test",
            )
        self.assertEqual(result["sandbox_backend"], "bubblewrap")
        self.assertEqual(len(fake.calls), 1)
        root, argv, kwargs = fake.calls[0]
        self.assertEqual(root, self.project.resolve())
        self.assertEqual(argv, ["/usr/bin/python3", "-c", "print('ok')"])
        self.assertEqual(kwargs["network_policy"], "deny")
        self.assertNotIn("stdin_text", kwargs)

    def test_allowlisted_network_and_backend_failure_fail_closed(self):
        engine = self.make_engine()
        allowlisted = self.grant(write=True, commands=["python"], network_policy="allowlisted")
        with self.assertRaisesRegex(Exception, "allowlisted is not implemented"):
            engine.tools.execute(
                "shell_exec", {"workspace_id": allowlisted["id"], "command": "python", "args": []},
                tenant_id="default", agent_id="software-engineer", actor="test",
            )

        grant = self.grant(write=True, commands=["python"])
        engine.tools.sandbox = FakeSandbox(fail="process sandbox backend is unavailable: namespace denied")
        with patch("zworkforce.workspace_tool_executor.shutil.which", return_value="/usr/bin/python3"):
            with self.assertRaisesRegex(Exception, "backend is unavailable"):
                engine.tools.execute(
                    "shell_exec", {"workspace_id": grant["id"], "command": "python", "args": []},
                    tenant_id="default", agent_id="software-engineer", actor="test",
                )

    def test_coder_uses_grant_root_and_does_not_require_shell_command_membership(self):
        engine = self.make_engine()
        fake = FakeSandbox()
        engine.tools.sandbox = fake
        grant = self.grant(write=True, commands=[])
        with patch("zworkforce.workspace_tool_executor.shutil.which", return_value="/usr/local/bin/zktcoder"), \
             patch("zworkforce.workspace_tool_executor.os.path.exists", return_value=True):
            result = engine.tools.execute(
                "zworkforce_code_agent",
                {"workspace_id": grant["id"], "prompt": "review only", "cwd": "subdir"},
                tenant_id="default", agent_id="software-engineer", actor="test",
            )
        self.assertEqual(result["sandbox_backend"], "bubblewrap")
        root, argv, kwargs = fake.calls[0]
        self.assertEqual(root, self.project.resolve())
        self.assertEqual(argv, ["/usr/local/bin/zktcoder", "--cwd", "/workspace/subdir"])
        self.assertEqual(kwargs["cwd_relative"], "subdir")
        self.assertEqual(kwargs["stdin_text"], "review only")

    def test_process_tool_events_exclude_shell_arguments_and_coder_prompt(self):
        engine = self.make_engine()
        fake = FakeSandbox()
        engine.tools.sandbox = fake
        grant = self.grant(write=True, commands=["python"])
        task, _ = engine.submit("default", "software-engineer", "process event test", actor="test", mutating=True)

        shell_secret = "SHELL-ARG-SECRET-SENTINEL"
        with patch("zworkforce.workspace_tool_executor.shutil.which", return_value="/usr/bin/python3"):
            shell_result = engine._execute_tool(
                task,
                "shell_exec",
                {"workspace_id": grant["id"], "command": "python", "args": ["-c", shell_secret]},
            )
        self.assertEqual(shell_result["exit_code"], 0)

        coder_secret = "CODER-PROMPT-SECRET-SENTINEL"
        with patch("zworkforce.workspace_tool_executor.shutil.which", return_value="/usr/local/bin/zktcoder"), \
             patch("zworkforce.workspace_tool_executor.os.path.exists", return_value=True):
            coder_result = engine._execute_tool(
                task,
                "zworkforce_code_agent",
                {"workspace_id": grant["id"], "prompt": coder_secret, "cwd": "."},
            )
        self.assertEqual(coder_result["exit_code"], 0)

        events = self.db.list_tool_events("default", task["id"], 20)
        serialized = json.dumps(events, ensure_ascii=False)
        self.assertNotIn(shell_secret, serialized)
        self.assertNotIn(coder_secret, serialized)
        by_name = {item["tool_name"]: item for item in events}
        self.assertEqual(by_name["shell_exec"]["args"]["argument_count"], 2)
        self.assertNotIn("args", by_name["shell_exec"]["args"])
        self.assertEqual(by_name["zworkforce_code_agent"]["args"]["prompt_bytes"], len(coder_secret.encode("utf-8")))
        self.assertNotIn("prompt", by_name["zworkforce_code_agent"]["args"])

    def test_development_without_workspace_id_keeps_legacy_process_path(self):
        settings = replace(self.settings, shell_enabled=True, embedded_workers=0)
        engine = PolicyEngine(settings, self.db, self.provider)
        self.engines.append(engine)
        py_cmd = "python3" if shutil.which("python3") else "python"
        result = engine.tools.execute(
            "shell_exec",
            {"command": py_cmd, "args": ["-c", "print('legacy-process-ok')"]},
            tenant_id="default",
            agent_id="software-engineer",
            actor="test",
        )
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("legacy-process-ok", result["stdout"])


if __name__ == "__main__":
    unittest.main()
