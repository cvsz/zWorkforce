import io
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib import error

from zworkforce.tools import TOOL_DEFINITIONS, ToolError, ToolExecutor
from zworkforce.zknowbase_client import (
    ZKnowbaseClient,
    ZKnowbaseConfig,
    ZKnowbaseError,
    ZKnowbaseRequestContext,
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


class ZKnowbaseClientTests(unittest.TestCase):
    def test_env_config_requires_url_and_key_together(self):
        with patch.dict(os.environ, {"ZWORKFORCE_ZKNOWBASE_URL": "http://zkb:8000"}, clear=True):
            with self.assertRaises(ValueError):
                ZKnowbaseConfig.from_env()

    def test_unconfigured_integration_is_optional(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(ZKnowbaseConfig.from_env())

    def test_tenant_key_map_is_parsed_and_cross_tenant_missing_key_fails_closed(self):
        env = {
            "ZWORKFORCE_ZKNOWBASE_URL": "http://zkb:8000",
            "ZWORKFORCE_ZKNOWBASE_TENANT_KEYS_JSON": json.dumps({"tenant-a": "key-a"}),
        }
        with patch.dict(os.environ, env, clear=True):
            config = ZKnowbaseConfig.from_env()
        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(config.key_for_tenant("tenant-a"), "key-a")
        with self.assertRaises(ZKnowbaseError):
            config.key_for_tenant("tenant-b")

    def test_single_key_is_bound_to_configured_tenant(self):
        config = ZKnowbaseConfig("http://zkb:8000", "secret-key", tenant_id="tenant-a")
        self.assertEqual(config.key_for_tenant("tenant-a"), "secret-key")
        with self.assertRaises(ZKnowbaseError):
            config.key_for_tenant("tenant-b")

    @patch("zworkforce.zknowbase_client.request.urlopen")
    def test_ask_uses_server_side_api_key(self, urlopen):
        urlopen.return_value = _Response({"answer": "Use the handbook", "sources": []})
        client = ZKnowbaseClient(ZKnowbaseConfig("http://zkb:8000", "secret-key"))
        result = client.ask("What is the leave policy?", top_k=3)
        self.assertEqual(result["answer"], "Use the handbook")
        req = urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "http://zkb:8000/api/v1/query")
        self.assertEqual(req.get_header("X-api-key"), "secret-key")
        self.assertEqual(
            json.loads(req.data),
            {"question": "What is the leave policy?", "top_k": 3, "stream": False},
        )

    @patch("zworkforce.zknowbase_client.request.urlopen")
    def test_search_contract(self, urlopen):
        urlopen.return_value = _Response(
            {"results": [{"document_name": "hr.md", "score": 0.91}]}
        )
        client = ZKnowbaseClient(ZKnowbaseConfig("http://zkb:8000", "secret-key"))
        result = client.search("annual leave", top_k=2)
        self.assertEqual(result["results"][0]["document_name"], "hr.md")

    @patch("zworkforce.zknowbase_client.request.urlopen")
    def test_tenant_search_sends_governed_context_and_validates_tenant(self, urlopen):
        urlopen.return_value = _Response(
            {"results": [{"document_name": "hr.md", "score": 0.91, "tenant_id": "tenant-a"}]}
        )
        client = ZKnowbaseClient(
            ZKnowbaseConfig(
                "http://zkb:8000",
                tenant_api_keys={"tenant-a": "read-only-a"},
            )
        )
        context = ZKnowbaseRequestContext(
            tenant_id="tenant-a",
            actor="user@example",
            agent_id="hr-agent",
            tool="knowledge_search",
            request_id="task-123",
            trace_id="tool-call-456",
        )
        result = client.search_for_tenant(context, "annual leave", top_k=2)
        self.assertEqual(result["results"][0]["tenant_id"], "tenant-a")
        req = urlopen.call_args.args[0]
        self.assertEqual(req.get_header("X-api-key"), "read-only-a")
        self.assertEqual(req.get_header("X-request-id"), "task-123")
        self.assertEqual(req.get_header("X-zworkforce-context-version"), "1")
        self.assertEqual(req.get_header("X-zworkforce-tenant-id"), "tenant-a")
        self.assertEqual(req.get_header("X-zworkforce-actor-id"), "user@example")
        self.assertEqual(req.get_header("X-zworkforce-agent-id"), "hr-agent")
        self.assertEqual(req.get_header("X-zworkforce-tool-id"), "knowledge_search")
        self.assertEqual(req.get_header("X-zworkforce-policy-context"), "agent_tool_grant")
        self.assertEqual(req.get_header("X-zworkforce-request-id"), "task-123")
        self.assertEqual(req.get_header("X-zworkforce-trace-id"), "tool-call-456")

    @patch("zworkforce.zknowbase_client.request.urlopen")
    def test_tenant_payload_mismatch_fails_closed(self, urlopen):
        urlopen.return_value = _Response(
            {"results": [{"document_name": "other.md", "score": 0.99, "tenant_id": "tenant-b"}]}
        )
        client = ZKnowbaseClient(
            ZKnowbaseConfig("http://zkb:8000", tenant_api_keys={"tenant-a": "key-a"})
        )
        context = ZKnowbaseRequestContext(
            tenant_id="tenant-a",
            actor="actor",
            agent_id="agent",
            tool="knowledge_search",
            request_id="task-1",
        )
        with self.assertRaises(ZKnowbaseError):
            client.search_for_tenant(context, "policy")

    def test_top_k_is_bounded(self):
        client = ZKnowbaseClient(ZKnowbaseConfig("http://zkb:8000", "secret-key"))
        with self.assertRaises(ZKnowbaseError):
            client.search("policy", top_k=21)

    def test_context_header_values_fail_closed_when_oversized(self):
        client = ZKnowbaseClient(
            ZKnowbaseConfig("http://zkb:8000", tenant_api_keys={"tenant-a": "key-a"})
        )
        context = ZKnowbaseRequestContext(
            tenant_id="tenant-a",
            actor="a" * 161,
            agent_id="agent",
            tool="knowledge_search",
            request_id="task-1",
        )
        with self.assertRaises(ZKnowbaseError):
            client.search_for_tenant(context, "policy")

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

    def test_governed_knowledge_tools_are_read_only(self):
        self.assertIn("knowledge_search", TOOL_DEFINITIONS)
        self.assertIn("knowledge_ask", TOOL_DEFINITIONS)
        self.assertFalse(TOOL_DEFINITIONS["knowledge_search"]["mutating"])
        self.assertFalse(TOOL_DEFINITIONS["knowledge_ask"]["mutating"])

    @patch("zworkforce.zknowbase_client.request.urlopen")
    def test_tool_executor_uses_governed_tenant_context(self, urlopen):
        urlopen.return_value = _Response(
            {"results": [{"document_name": "tenant.md", "score": 0.8, "tenant_id": "tenant-a"}]}
        )
        settings = SimpleNamespace(
            workspace_root=Path("."),
            max_request_bytes=1_048_576,
        )
        executor = ToolExecutor(settings, SimpleNamespace())
        env = {
            "ZWORKFORCE_ZKNOWBASE_URL": "http://zkb:8000",
            "ZWORKFORCE_ZKNOWBASE_TENANT_KEYS_JSON": json.dumps({"tenant-a": "read-a"}),
        }
        with patch.dict(os.environ, env, clear=True):
            result = executor.execute(
                "knowledge_search",
                {"query": "policy", "top_k": 3},
                tenant_id="tenant-a",
                agent_id="policy-agent",
                actor="agent:policy-agent",
                request_id="task-55",
                policy_context="agent_tool_grant",
            )
        self.assertEqual(result["results"][0]["tenant_id"], "tenant-a")
        req = urlopen.call_args.args[0]
        self.assertEqual(req.get_header("X-request-id"), "task-55")
        self.assertEqual(req.get_header("X-zworkforce-tenant-id"), "tenant-a")
        self.assertEqual(req.get_header("X-zworkforce-trace-id"), "task-55")
        self.assertEqual(req.get_header("X-api-key"), "read-a")

    def test_tool_executor_fails_closed_without_tenant_credential(self):
        settings = SimpleNamespace(workspace_root=Path("."), max_request_bytes=1_048_576)
        executor = ToolExecutor(settings, SimpleNamespace())
        env = {
            "ZWORKFORCE_ZKNOWBASE_URL": "http://zkb:8000",
            "ZWORKFORCE_ZKNOWBASE_TENANT_KEYS_JSON": json.dumps({"tenant-a": "read-a"}),
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ToolError):
                executor.execute(
                    "knowledge_search",
                    {"query": "policy"},
                    tenant_id="tenant-b",
                    agent_id="agent",
                    actor="actor",
                )


if __name__ == "__main__":
    unittest.main()
