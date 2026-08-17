from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from tests.common import stack
from zworkforce.policy import PolicyEngine

ROOT = Path(__file__).resolve().parents[1]


class ProcessSandboxContractTests(unittest.TestCase):
    def test_production_image_installs_bubblewrap_and_prlimit_provider(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("bubblewrap", dockerfile)
        self.assertIn("util-linux", dockerfile)
        self.assertIn("USER 10001:10001", dockerfile)

    def test_shell_args_must_be_array_even_when_called_outside_tool_schema(self):
        temp, settings, db, provider, dev_engine, _ = stack()
        project = settings.workspace_root / "process-contract"
        project.mkdir(parents=True)
        expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(timespec="seconds")
        grant = db.upsert_workspace_grant(
            "default",
            {
                "name": "Process contract",
                "root_rel": "process-contract",
                "read": True,
                "write": True,
                "commands": ["python"],
                "network_policy": "deny",
                "enabled": True,
                "expires_at": expires,
            },
            "test",
        )
        engine = PolicyEngine(replace(settings, env="production", embedded_workers=0, shell_enabled=True), db, provider)
        try:
            with self.assertRaisesRegex(Exception, "shell args must be an array"):
                engine.tools.execute(
                    "shell_exec",
                    {"workspace_id": grant["id"], "command": "python", "args": "-V"},
                    tenant_id="default",
                    agent_id="software-engineer",
                    actor="test",
                )
        finally:
            engine.shutdown()
            dev_engine.shutdown()
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
