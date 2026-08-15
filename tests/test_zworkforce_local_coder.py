import unittest
from unittest.mock import patch, MagicMock

from tests.common import stack
from zworkforce.config import ProviderConfig
from zworkforce.providers import ZworkforceLocalEndpoint, ProviderPool
from zworkforce.tools import ToolExecutor, ToolError


class ZworkforceLocalCoderTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()

    def tearDown(self):
        self.engine.shutdown()
        self.temp.cleanup()

    def test_zworkforce_local_endpoint_invocation(self):
        cfg = ProviderConfig(name="zwf-native", kind="zworkforce-local", models={"luna": "deepseek/deepseek-v4-flash"})
        endpoint = ZworkforceLocalEndpoint(cfg)

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Task code generated."
        mock_proc.stderr = ""

        with patch("os.path.exists", return_value=True), patch("subprocess.run", return_value=mock_proc):
            res = endpoint.chat("luna", [{"role": "user", "content": "Write hello world"}], [])

        self.assertEqual(res.provider_name, "zwf-native")
        self.assertEqual(res.model, "deepseek/deepseek-v4-flash")
        self.assertEqual(res.content, "Task code generated.")
        self.assertGreater(res.usage.output_tokens, 0)

    def test_zworkforce_code_agent_tool_execution(self):
        executor = ToolExecutor(self.settings, self.db)

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Files refactored cleanly."
        mock_proc.stderr = ""

        with patch("os.path.exists", return_value=True), patch("subprocess.run", return_value=mock_proc):
            result = executor.execute(
                "zworkforce_code_agent",
                {"prompt": "Refactor math utils", "cwd": "."},
                tenant_id="default",
                agent_id="software-engineer",
                actor="test-dev",
            )

        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["stdout"], "Files refactored cleanly.")


if __name__ == "__main__":
    unittest.main()
