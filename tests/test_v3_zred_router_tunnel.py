from __future__ import annotations

import unittest

from zworkforce.safety_hooks import SafetyHookRegistry, SafetyViolationError
from zworkforce.solana_notary import SolanaNotaryClient, NotaryReceipt
from zworkforce.router_tracing import RouterTelemetryCollector
from zworkforce.tunnel_client import McpTunnelClient, TunnelClientError


class SafetyHookTests(unittest.TestCase):
    def setUp(self):
        self.hooks = SafetyHookRegistry()

    def test_blocks_dangerous_bash_commands(self):
        with self.assertRaises(SafetyViolationError) as ctx:
            self.hooks.pre_tool_hook("run_command", {"CommandLine": "rm -rf /"})
        self.assertIn("blocked dangerous command", str(ctx.exception))

    def test_blocks_destructive_database_drop(self):
        with self.assertRaises(SafetyViolationError) as ctx:
            self.hooks.pre_tool_hook("sql_query", {"query": "DROP DATABASE production;"})
        self.assertIn("blocked destructive database query", str(ctx.exception))

    def test_post_tool_pii_redaction(self):
        raw = "User email is alice@example.com and card is 4111-2222-3333-4444"
        sanitized = self.hooks.post_tool_hook("fetch_data", raw)
        self.assertNotIn("alice@example.com", sanitized)
        self.assertIn("[EMAIL_REDACTED]", sanitized)
        self.assertIn("[CREDIT_CARD_REDACTED]", sanitized)


class SolanaNotaryTests(unittest.TestCase):
    def setUp(self):
        self.notary = SolanaNotaryClient(network="devnet")

    def test_notarize_and_verify(self):
        payload = "release-v3.0.3-sha256-checksums"
        receipt = self.notary.notarize_content("tenant-alpha", payload, {"version": "3.0.3"})
        self.assertEqual(receipt.network, "devnet")
        self.assertTrue(receipt.tx_signature.startswith("sol-tx-"))

        is_valid = self.notary.verify_receipt(receipt, payload)
        self.assertTrue(is_valid)

        is_tampered = self.notary.verify_receipt(receipt, "tampered-content")
        self.assertFalse(is_tampered)


class RouterTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.collector = RouterTelemetryCollector()

    def test_record_free_vs_paid_model_costs(self):
        span_free = self.collector.record_usage("t1", "deepseek/deepseek-r1:free", 1000, 500, 250.0)
        self.assertEqual(span_free.total_cost_usd, 0.0)

        span_paid = self.collector.record_usage("t1", "anthropic/claude-3.5-sonnet", 1_000_000, 0, 800.0)
        self.assertEqual(span_paid.total_cost_usd, 3.00)

        summary = self.collector.get_tenant_summary("t1")
        self.assertEqual(summary["total_requests"], 2)
        self.assertEqual(summary["total_cost_usd"], 3.00)


class McpTunnelClientTests(unittest.TestCase):
    def test_tunnel_client_lifecycle(self):
        client = McpTunnelClient("t1", "edge-daemon-1")
        self.assertFalse(client.connected)

        conn = client.connect()
        self.assertTrue(client.connected)
        self.assertEqual(conn["status"], "connected")

        hb = client.send_heartbeat()
        self.assertTrue(hb)

        client.disconnect()
        self.assertFalse(client.connected)
        with self.assertRaises(TunnelClientError):
            client.send_heartbeat()


if __name__ == "__main__":
    unittest.main()
