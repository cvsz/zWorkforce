from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from zworkforce.cli import main


class CliSecurityTests(unittest.TestCase):
    def _run_key_create(self, root: Path, *extra: str) -> tuple[int, str, str]:
        env = {
            "ZWORKFORCE_ENV": "development",
            "ZWORKFORCE_PROVIDER": "mock",
            "ZWORKFORCE_API_KEYS": "bootstrap-test-secret:superadmin:default:bootstrap",
            "ZWORKFORCE_DATA_DIR": str(root / "data"),
            "ZWORKFORCE_WORKSPACE_ROOT": str(root / "workspace"),
            "ZWORKFORCE_EMBEDDED_WORKERS": "0",
        }
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.dict(os.environ, env, clear=True), redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["key-create", "--name", "cli-test", *extra])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_key_create_writes_secret_only_to_mode_0600_file(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output, error = self._run_key_create(Path(directory))
            self.assertEqual(code, 0, error)
            payload = json.loads(output)
            self.assertNotIn("secret", payload)
            secret_path = Path(payload["secret_file"])
            self.assertTrue(secret_path.is_file())
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(secret_path.stat().st_mode), 0o600)
            else:
                self.assert_windows_acl_is_owner_only(secret_path)
            secret = secret_path.read_text(encoding="utf-8").strip()
            self.assertTrue(secret.startswith("zwf_"))
            self.assertNotIn(secret, output)

    def test_key_create_refuses_to_overwrite_secret_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing.secret"
            target.write_text("keep-me\n", encoding="utf-8")
            target.chmod(0o644)
            code, output, error = self._run_key_create(Path(directory), "--secret-file", str(target))
            self.assertEqual(code, 1)
            self.assertEqual(output, "")
            self.assertIn("secret file already exists", error)
            self.assertEqual(target.read_text(encoding="utf-8"), "keep-me\n")
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)

    def assert_windows_acl_is_owner_only(self, path: Path) -> None:
        output = subprocess.check_output(["icacls", str(path)], text=True, encoding="utf-8")
        access_lines = [
            line.strip()
            for line in output.splitlines()
            if line.strip() and not line.startswith("Successfully processed")
        ]
        self.assertEqual(len(access_lines), 1, output)
        self.assertNotIn("(I)", access_lines[0], output)
        self.assertIn("(F)", access_lines[0], output)


if __name__ == "__main__":
    unittest.main()
