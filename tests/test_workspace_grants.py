import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

from tests.common import stack
from zworkforce.db import SCHEMA_VERSION
from zworkforce.workspace_grant_api import WorkspaceGrantApp
from zworkforce.workspace_grants import WorkspaceGrantError, WorkspaceGrantService


class WorkspaceGrantTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()
        self.project = self.settings.workspace_root / "project-a"
        self.project.mkdir(parents=True)
        self.service = WorkspaceGrantService(self.settings, self.db)
        self.app = WorkspaceGrantApp(self.settings, self.db, self.engine, self.auth, self.provider)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.app.handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.engine.shutdown()
        self.temp.cleanup()

    @staticmethod
    def future(hours=1):
        return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat(timespec="seconds")

    def req(self, path, method="GET", body=None, headers=None, token="test-admin-secret", timeout=10):
        request_headers = {"Authorization": f"Bearer {token}", **(headers or {})}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base + path, data=data, headers=request_headers, method=method)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read())

    def error(self, path, method="GET", body=None, headers=None, token="test-admin-secret"):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.req(path, method, body, headers, token)
        return ctx.exception.code, json.loads(ctx.exception.read())

    def grant_body(self, **overrides):
        body = {
            "name": "Project A",
            "root": "project-a",
            "read": True,
            "write": False,
            "commands": ["git"],
            "network_policy": "deny",
            "expires_at": self.future(),
        }
        body.update(overrides)
        return body

    def test_schema_v7_and_grant_api_round_trip(self):
        self.assertEqual(SCHEMA_VERSION, 7)
        status, grant = self.req("/api/v1/workspaces/grants", "POST", self.grant_body())
        self.assertEqual(status, 201)
        self.assertEqual(grant["root_rel"], "project-a")
        self.assertTrue(grant["read"])
        self.assertFalse(grant["write"])
        self.assertEqual(grant["commands"], ["git"])
        self.assertEqual(grant["network_policy"], "deny")

        status, listing = self.req("/api/v1/workspaces/grants")
        self.assertEqual(status, 200)
        self.assertEqual([item["id"] for item in listing["items"]], [grant["id"]])

        stored = self.db.get_workspace_grant("default", grant["id"])
        self.assertEqual(stored["root_rel"], "project-a")
        self.assertEqual(stored["commands"], ["git"])

        status, result = self.req(f"/api/v1/workspaces/grants/{grant['id']}/disable", "POST", {})
        self.assertEqual(status, 200)
        self.assertTrue(result["disabled"])
        with self.assertRaisesRegex(WorkspaceGrantError, "disabled"):
            self.service.resolve_root("default", grant["id"], require_read=True)

    def test_grants_are_tenant_scoped_and_admin_only(self):
        _, grant = self.req("/api/v1/workspaces/grants", "POST", self.grant_body())
        self.req("/api/v1/tenants", "POST", {"id": "acme", "name": "Acme"})
        status, listing = self.req("/api/v1/workspaces/grants", headers={"X-Tenant-ID": "acme"})
        self.assertEqual(status, 200)
        self.assertEqual(listing["items"], [])
        self.assertIsNone(self.db.get_workspace_grant("acme", grant["id"]))

        _, operator = self.auth.create_key("default", "grant-operator", "operator", ["workspace:grant"])
        status, payload = self.error("/api/v1/workspaces/grants", token=operator)
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["code"], "auth_failed")

    def test_root_must_be_existing_relative_directory_inside_host_ceiling(self):
        for root in (str(self.project.resolve()), "../escape", "C:\\Windows", "missing-directory"):
            status, payload = self.error(
                "/api/v1/workspaces/grants",
                "POST",
                self.grant_body(root=root),
            )
            self.assertEqual(status, 400)
            self.assertEqual(payload["error"]["code"], "invalid_request")

    def test_symlink_escape_and_post_grant_swap_fail_closed(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink support unavailable")
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        link = self.settings.workspace_root / "escape-link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation unavailable")
        with self.assertRaisesRegex(WorkspaceGrantError, "escapes"):
            self.service.normalize_root("escape-link")

        status, grant = self.req("/api/v1/workspaces/grants", "POST", self.grant_body())
        self.assertEqual(status, 201)
        self.project.rmdir()
        try:
            self.project.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("symlink replacement unavailable")
        with self.assertRaises(WorkspaceGrantError):
            self.service.resolve_root("default", grant["id"], require_read=True)

    def test_expiry_and_command_allowlist_fail_closed(self):
        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(timespec="seconds")
        too_far = (datetime.now(timezone.utc) + timedelta(days=366)).isoformat(timespec="seconds")
        for expires_at in (past, too_far, "2030-01-01T00:00:00"):
            status, payload = self.error(
                "/api/v1/workspaces/grants",
                "POST",
                self.grant_body(expires_at=expires_at),
            )
            self.assertEqual(status, 400)
            self.assertEqual(payload["error"]["code"], "invalid_request")

        status, payload = self.error(
            "/api/v1/workspaces/grants",
            "POST",
            self.grant_body(commands=["git", "definitely-not-allowlisted"]),
        )
        self.assertEqual(status, 400)
        self.assertIn("shell allowlist", payload["error"]["message"])


if __name__ == "__main__":
    unittest.main()
