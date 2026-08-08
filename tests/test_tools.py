import tempfile,unittest
from pathlib import Path
from zworkforce.config import Settings
from zworkforce.tools import ToolExecutor,ToolError
class ToolTests(unittest.TestCase):
    def test_calculator(self):
        with tempfile.TemporaryDirectory() as d: self.assertEqual(ToolExecutor(Settings(workspace_root=Path(d))).execute("calculator",{"expression":"2*(3+4)"}),14)
    def test_path_escape(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ToolError): ToolExecutor(Settings(workspace_root=Path(d))).execute("workspace_read",{"path":"../../etc/passwd"})
    def test_shell_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ToolError): ToolExecutor(Settings(workspace_root=Path(d))).execute("shell_exec",{"command":"python","args":["-V"]})
