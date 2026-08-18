from __future__ import annotations

import time
import unittest

from zworkforce.tunnel import McpTunnelManager, TunnelError


class McpTunnelTests(unittest.TestCase):
    def setUp(self):
        self.manager = McpTunnelManager(heartbeat_timeout_seconds=2.0)

    def test_register_tunnel_success(self):
        conn = self.manager.register_tunnel("tenant-1", "client-local-1", [{"name": "local_grep"}])
        self.assertTrue(conn.tunnel_id.startswith("tun-"))
        self.assertEqual(conn.tenant_id, "tenant-1")
        self.assertEqual(conn.client_id, "client-local-1")
        self.assertEqual(len(conn.exposed_tools), 1)

    def test_register_tunnel_validation_fails_closed(self):
        with self.assertRaises(TunnelError):
            self.manager.register_tunnel("", "client-1")
        with self.assertRaises(TunnelError):
            self.manager.register_tunnel("tenant-1", "")

    def test_tunnel_heartbeat_and_timeout(self):
        conn = self.manager.register_tunnel("tenant-1", "client-1")
        self.manager.record_heartbeat(conn.tunnel_id)
        active = self.manager.get_tunnel("tenant-1", conn.tunnel_id)
        self.assertEqual(active.tunnel_id, conn.tunnel_id)

        # Wait for timeout expiration
        time.sleep(2.1)
        with self.assertRaises(TunnelError) as ctx:
            self.manager.get_tunnel("tenant-1", conn.tunnel_id)
        self.assertIn("heartbeat timed out", str(ctx.exception))

    def test_cross_tenant_tunnel_access_denied(self):
        conn = self.manager.register_tunnel("tenant-alpha", "client-1")
        with self.assertRaises(TunnelError):
            self.manager.get_tunnel("tenant-beta", conn.tunnel_id)

    def test_cross_tenant_close_does_not_affect_other_tenant(self):
        conn = self.manager.register_tunnel("tenant-alpha", "client-1")
        self.assertFalse(self.manager.close_tunnel("tenant-beta", conn.tunnel_id))
        self.assertEqual(self.manager.get_tunnel("tenant-alpha", conn.tunnel_id).tunnel_id, conn.tunnel_id)

    def test_per_tenant_tunnel_limit_enforced(self):
        manager = McpTunnelManager(heartbeat_timeout_seconds=30.0, max_tunnels_per_tenant=2)
        manager.register_tunnel("tenant-1", "client-1")
        manager.register_tunnel("tenant-1", "client-2")
        with self.assertRaises(TunnelError) as ctx:
            manager.register_tunnel("tenant-1", "client-3")
        self.assertIn("tunnel limit", str(ctx.exception))
        # A different tenant is not affected by tenant-1's limit
        manager.register_tunnel("tenant-2", "client-1")

    def test_prune_stale_reaps_expired_and_evicts_inactive(self):
        conn = self.manager.register_tunnel("tenant-1", "client-1")
        now = time.time()
        report = self.manager.prune_stale(now=now + 10.0)
        self.assertEqual(report["reaped"], 1)
        self.assertEqual(report["remaining"], 0)
        with self.assertRaises(TunnelError):
            self.manager.get_tunnel("tenant-1", conn.tunnel_id)

    def test_prune_stale_keeps_healthy_tunnels_and_evicts_closed(self):
        conn = self.manager.register_tunnel("tenant-1", "client-1")
        other = self.manager.register_tunnel("tenant-2", "client-2")
        now = time.time()
        self.manager.close_tunnel("tenant-1", conn.tunnel_id)
        self.assertEqual(len(self.manager._tunnels), 1)
        report = self.manager.prune_stale(now=now)
        self.assertEqual(report["reaped"], 0)
        self.assertEqual(report["remaining"], 1)
        self.assertEqual(self.manager.list_active_tunnels("tenant-2")[0]["tunnel_id"], other.tunnel_id)

    def test_audit_callback_receives_lifecycle_events(self):
        events = []
        manager = McpTunnelManager(
            heartbeat_timeout_seconds=2.0,
            audit=lambda tenant_id, action, details: events.append((tenant_id, action, dict(details))),
        )
        conn = manager.register_tunnel("tenant-1", "client-1")
        manager.record_heartbeat(conn.tunnel_id)
        manager.close_tunnel("tenant-1", conn.tunnel_id)
        manager.prune_stale(now=time.time())
        actions = [event[1] for event in events]
        self.assertEqual(actions, ["tunnel.register", "tunnel.close"])

    def test_heartbeat_timeout_evicts_registry_entry(self):
        conn = self.manager.register_tunnel("tenant-1", "client-1")
        time.sleep(2.1)
        with self.assertRaises(TunnelError):
            self.manager.get_tunnel("tenant-1", conn.tunnel_id)
        self.assertEqual(self.manager.prune_stale()["remaining"], 0)

    def test_list_and_close_tunnel(self):
        conn1 = self.manager.register_tunnel("tenant-1", "client-1")
        conn2 = self.manager.register_tunnel("tenant-1", "client-2")
        tunnels = self.manager.list_active_tunnels("tenant-1")
        self.assertEqual(len(tunnels), 2)

        closed = self.manager.close_tunnel("tenant-1", conn1.tunnel_id)
        self.assertTrue(closed)
        tunnels_after = self.manager.list_active_tunnels("tenant-1")
        self.assertEqual(len(tunnels_after), 1)
        self.assertEqual(tunnels_after[0]["tunnel_id"], conn2.tunnel_id)


if __name__ == "__main__":
    unittest.main()
