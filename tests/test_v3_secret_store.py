import json
import os
import tempfile
import unittest
from pathlib import Path

from zworkforce.secret_store import SecretResolver, SecretStoreError


class SecretStoreTests(unittest.TestCase):
    def test_env_and_file_json_field(self):
        os.environ["ZWF_TEST_SECRET"]="value-123"
        self.assertEqual(SecretResolver().resolve("env://ZWF_TEST_SECRET"),"value-123")
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"secret.json";p.write_text(json.dumps({"token":"abc"}))
            self.assertEqual(SecretResolver().resolve(p.as_uri()+"#token"),"abc")
    def test_unsupported_scheme_rejected(self):
        with self.assertRaises(SecretStoreError): SecretResolver().resolve("ftp://example/secret")

if __name__=="__main__": unittest.main()
