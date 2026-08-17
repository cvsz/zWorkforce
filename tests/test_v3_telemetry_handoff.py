from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zworkforce.telemetry import OtlpHttpExporter, wrap_provider_from_env, _TelemetryProvider
from zworkforce.agent_handoff import AgentHandoffProtocol, HandoffContract, AgentHandoffError


class TelemetryTests(unittest.TestCase):
    def test_otlp_exporter_rejects_insecure_remote_urls(self):
        with self.assertRaises(ValueError):
            OtlpHttpExporter("http://collector.example.com/v1/traces")
        with self.assertRaises(ValueError):
            OtlpHttpExporter("invalid-url")

    def test_otlp_exporter_accepts_localhost_http(self):
        exporter = OtlpHttpExporter("http://localhost:4318/v1/traces")
        self.assertEqual(exporter.endpoint, "http://localhost:4318/v1/traces")

    def test_otlp_exporter_accepts_https(self):
        exporter = OtlpHttpExporter("https://otlp.grafana.net/v1/traces", headers={"Authorization": "Bearer token"})
        self.assertEqual(exporter.service_name, "zworkforce")

    def test_otlp_exporter_redacts_sensitive_attributes(self):
        exporter = OtlpHttpExporter("http://localhost:4318/v1/traces")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"{}"
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            exporter.export(
                "test.span",
                1000000,
                2000000,
                {"api_key": "sk-secret123", "password": "supersecret", "normal": "val"},
            )
            self.assertTrue(mock_urlopen.called)
            req = mock_urlopen.call_args[0][0]
            body = req.data.decode("utf-8")
            self.assertNotIn("sk-secret123", body)
            self.assertNotIn("supersecret", body)
            self.assertIn("[REDACTED]", body)

    def test_wrap_provider_from_env(self):
        mock_provider = MagicMock()
        mock_provider.chat.return_value = MagicMock(usage=MagicMock(input_tokens=10, cached_tokens=2, output_tokens=20), provider_name="mock", model="mock-model")

        with patch.dict("os.environ", {"ZWORKFORCE_OTLP_TRACES_ENDPOINT": "http://127.0.0.1:4318/v1/traces", "ZWORKFORCE_OTLP_HEADERS_JSON": "{\"X-Test\": \"1\"}"}):
            wrapped = wrap_provider_from_env(mock_provider)
            self.assertIsInstance(wrapped, _TelemetryProvider)
            result = wrapped.chat("luna", [{"role": "user", "content": "hi"}], [])
            self.assertIsNotNone(result)


class AgentHandoffTests(unittest.TestCase):
    def setUp(self):
        self.protocol = AgentHandoffProtocol([
            HandoffContract(
                source_agent_id="researcher",
                target_agent_id="writer",
                required_inputs=("prompt", "outline"),
                max_context_tokens=2000,
                allow_mutating=False,
                validation_schema={"type": "object", "properties": {"prompt": {"type": "string"}, "outline": {"type": "string"}}},
            )
        ])

    def test_self_delegation_is_rejected(self):
        with self.assertRaises(AgentHandoffError) as ctx:
            self.protocol.validate_handoff("agent-a", "agent-a", {"prompt": "task"})
        self.assertIn("cannot delegate directly to itself", str(ctx.exception))

    def test_empty_target_is_rejected(self):
        with self.assertRaises(AgentHandoffError) as ctx:
            self.protocol.validate_handoff("agent-a", "", {"prompt": "task"})
        self.assertIn("target agent_id is required", str(ctx.exception))

    def test_contract_missing_required_parameter(self):
        with self.assertRaises(AgentHandoffError) as ctx:
            self.protocol.validate_handoff("researcher", "writer", {"prompt": "write article"})
        self.assertIn("missing required parameter 'outline'", str(ctx.exception))

    def test_contract_mutating_action_denied(self):
        with self.assertRaises(AgentHandoffError) as ctx:
            self.protocol.validate_handoff("researcher", "writer", {"prompt": "write", "outline": "1"}, is_mutating=True)
        self.assertIn("does not permit mutating actions", str(ctx.exception))

    def test_contract_token_limit_exceeded(self):
        with self.assertRaises(AgentHandoffError) as ctx:
            self.protocol.validate_handoff("researcher", "writer", {"prompt": "write", "outline": "1"}, estimated_tokens=5000)
        self.assertIn("exceeds maximum contract limit", str(ctx.exception))

    def test_valid_handoff_passes_and_compacts(self):
        validated = self.protocol.validate_handoff(
            "researcher",
            "writer",
            {"prompt": "draft intro", "outline": "summary", "custom_num": 42},
            estimated_tokens=500,
        )
        self.assertEqual(validated["prompt"], "draft intro")
        self.assertEqual(validated["outline"], "summary")
        self.assertEqual(validated["custom_num"], 42)


if __name__ == "__main__":
    unittest.main()
