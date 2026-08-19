import io
import json
import os
import unittest
from unittest.mock import patch
from urllib import error

from zworkforce.zknowbase_client import ZKnowbaseClient, ZKnowbaseConfig, ZKnowbaseError


class _Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class ZKnowbaseClientTests(unittest.TestCase):
    def test_env_config_requires_url_and_key_together(self):
        with patch.dict(os.environ, {"ZWORKFORCE_ZKNOWBASE_URL": "http://zkb:8000"}, clear=True):
            with self.assertRaises(ValueError):
                ZKnowbaseConfig.from_env()

    def test_unconfigured_integration_is_optional(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(ZKnowbaseConfig.from_env())

    @patch("zworkforce.zknowbase_client.request.urlopen")
    def test_ask_uses_server_side_api_key(self, urlopen):
        urlopen.return_value = _Response({"answer": "Use the handbook", "sources": []})
        client = ZKnowbaseClient(ZKnowbaseConfig("http://zkb:8000", "secret-key"))
        result = client.ask("What is the leave policy?", top_k=3)
        self.assertEqual(result["answer"], "Use the handbook")
        req = urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "http://zkb:8000/api/v1/query")
        self.assertEqual(req.get_header("X-api-key"), "secret-key")
        self.assertEqual(json.loads(req.data), {"question": "What is the leave policy?", "top_k": 3, "stream": False})

    @patch("zworkforce.zknowbase_client.request.urlopen")
    def test_search_contract(self, urlopen):
        urlopen.return_value = _Response({"results": [{"document_name": "hr.md", "score": 0.91}]})
        client = ZKnowbaseClient(ZKnowbaseConfig("http://zkb:8000", "secret-key"))
        result = client.search("annual leave", top_k=2)
        self.assertEqual(result["results"][0]["document_name"], "hr.md")

    @patch("zworkforce.zknowbase_client.request.urlopen")
    def test_http_error_is_bounded_and_wrapped(self, urlopen):
        urlopen.side_effect = error.HTTPError("http://zkb", 401, "Unauthorized", {}, io.BytesIO(b'{"detail":"bad key"}'))
        client = ZKnowbaseClient(ZKnowbaseConfig("http://zkb:8000", "secret-key"))
        with self.assertRaises(ZKnowbaseError) as ctx:
            client.health()
        self.assertIn("HTTP 401", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
