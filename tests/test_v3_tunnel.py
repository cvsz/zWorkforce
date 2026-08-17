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

    def test_list_and_close_tunnel(self):
        conn1 = self.manager.register_tunnel("tenant-1", "client-1")
        conn2 = self.manager.register_tunnel("tenant-1", "client-2")
        tunnels = self.manager.list_active_tunnels("tenant-1")
        self.assertEqual(len(tunnels), 2)

        closed = self.manager.close_tunnel("tenant-1", conn1.tunnel_id)
        self.assertTrue(closed)
        tunnels_after = self.manager.list_active_tunnels("tenant-1")
        self.assertEqual(len(tunnels_after), 1)


if __name__ == "__main__":
    unittest.main()
