import io
import json
import os
import unittest
from unittest.mock import patch
from urllib import error

from zworkforce.zknowbase_client import (
    ZKnowbaseClient,
    ZKnowbaseConfig,
    ZKnowbaseError,
    ZKnowbaseExecutionContext,
)


class _Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def _context(**overrides):
    values = {
        "tenant_id": "tenant-a",
        "actor_id": "actor-7",
        "agent_id": "agent-policy",
        "tool_id": "knowledge.search",
        "policy_context": "policy-evaluation-42",
        "request_id": "request-123",
        "trace_id": "trace-abc",
    }
    values.update(overrides)
    return ZKnowbaseExecutionContext(**values)


class ZKnowbaseClientTests(unittest.TestCase):
    def test_env_config_requires_url_and_key_together(self):
        with patch.dict(os.environ, {"ZWORKFORCE_ZKNOWBASE_URL": "http://zkb:8000"}, clear=True):
            with self.assertRaises(ValueError):
                ZKnowbaseConfig.from_env()

    def test_unconfigured_integration_is_optional(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(ZKnowbaseConfig.from_env())

    def test_execution_context_rejects_missing_or_unbounded_values(self):
        with self.assertRaisesRegex(ValueError, "actor_id"):
            _context(actor_id=" ").headers()
        with self.assertRaisesRegex(ValueError, "policy_context"):
            _context(policy_context="x" * 257).headers()
        with self.assertRaisesRegex(ValueError, "trace_id"):
            _context(trace_id="trace\nspoof").headers()

    @patch("zworkforce.zknowbase_client.request.urlopen")
    def test_ask_uses_server_side_api_key_and_governed_context(self, urlopen):
        urlopen.return_value = _Response({"answer": "Use the handbook", "sources": []})
        client = ZKnowbaseClient(ZKnowbaseConfig("http://zkb:8000", "secret-key"))
        result = client.ask("What is the leave policy?", context=_context(), top_k=3)
        self.assertEqual(result["answer"], "Use the handbook")
        req = urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "http://zkb:8000/api/v1/query")
        self.assertEqual(req.get_header("X-api-key"), "secret-key")
        self.assertEqual(req.get_header("X-request-id"), "request-123")
        self.assertEqual(req.get_header("X-zworkforce-context-version"), "1")
        self.assertEqual(req.get_header("X-zworkforce-tenant-id"), "tenant-a")
        self.assertEqual(req.get_header("X-zworkforce-actor-id"), "actor-7")
        self.assertEqual(req.get_header("X-zworkforce-agent-id"), "agent-policy")
        self.assertEqual(req.get_header("X-zworkforce-tool-id"), "knowledge.search")
        self.assertEqual(
            req.get_header("X-zworkforce-policy-context"), "policy-evaluation-42"
        )
        self.assertEqual(req.get_header("X-zworkforce-request-id"), "request-123")
        self.assertEqual(req.get_header("X-zworkforce-trace-id"), "trace-abc")
        self.assertEqual(
            json.loads(req.data),
            {"question": "What is the leave policy?", "top_k": 3, "stream": False},
        )

    @patch("zworkforce.zknowbase_client.request.urlopen")
    def test_search_contract_propagates_governance_context(self, urlopen):
        urlopen.return_value = _Response(
            {"results": [{"document_name": "hr.md", "score": 0.91}]}
        )
        client = ZKnowbaseClient(ZKnowbaseConfig("http://zkb:8000", "secret-key"))
        result = client.search("annual leave", context=_context(tool_id="knowledge.search"), top_k=2)
        self.assertEqual(result["results"][0]["document_name"], "hr.md")
        req = urlopen.call_args.args[0]
        self.assertEqual(req.get_header("X-zworkforce-tenant-id"), "tenant-a")
        self.assertEqual(req.get_header("X-zworkforce-tool-id"), "knowledge.search")

    def test_retrieval_requires_governed_context_at_call_boundary(self):
        client = ZKnowbaseClient(ZKnowbaseConfig("http://zkb:8000", "secret-key"))
        with self.assertRaises(TypeError):
            client.ask("policy")  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            client.search("policy")  # type: ignore[call-arg]

    @patch("zworkforce.zknowbase_client.request.urlopen")
    def test_health_does_not_send_governed_retrieval_headers(self, urlopen):
        urlopen.return_value = _Response({"status": "ok"})
        client = ZKnowbaseClient(ZKnowbaseConfig("http://zkb:8000", "secret-key"))
        result = client.health()
        self.assertEqual(result["status"], "ok")
        req = urlopen.call_args.args[0]
        self.assertIsNone(req.get_header("X-zworkforce-context-version"))

    @patch("zworkforce.zknowbase_client.request.urlopen")
    def test_http_error_is_bounded_and_wrapped(self, urlopen):
        urlopen.side_effect = error.HTTPError(
            "http://zkb",
            401,
            "Unauthorized",
            {},
            io.BytesIO(b'{"detail":"bad key"}'),
        )
        client = ZKnowbaseClient(ZKnowbaseConfig("http://zkb:8000", "secret-key"))
        with self.assertRaises(ZKnowbaseError) as ctx:
            client.health()
        self.assertIn("HTTP 401", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
