import json
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

from common import stack
from zworkforce.workspace_api import WorkspaceApp


class WorkspaceApiTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()
        self.app = WorkspaceApp(self.settings, self.db, self.engine, self.auth, self.provider)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.app.handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.engine.shutdown()
        self.temp.cleanup()

    def req(self, path, method="GET", body=None, headers=None, token="test-admin-secret", timeout=10):
        request_headers = {"Authorization": f"Bearer {token}", **(headers or {})}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base + path,
            data=data,
            headers=request_headers,
            method=method,
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers), json.loads(response.read())

    def error(self, path, method="GET", body=None, headers=None, token="test-admin-secret"):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.req(path, method, body, headers, token)
        payload = json.loads(ctx.exception.read())
        return ctx.exception.code, payload

    def test_project_conversation_message_flow_and_core_api_passthrough(self):
        overview_status, _, overview = self.req("/api/v1/overview")
        self.assertEqual(overview_status, 200)
        self.assertIn("credits_24h", overview)

        status, _, project = self.req(
            "/api/v1/workspaces/projects",
            "POST",
            {"name": "Workspace Alpha", "description": "durable project"},
        )
        self.assertEqual(status, 201)

        status, _, conversation = self.req(
            "/api/v1/workspaces/conversations",
            "POST",
            {"project_id": project["id"], "title": "First conversation"},
        )
        self.assertEqual(status, 201)

        status, _, message = self.req(
            f"/api/v1/workspaces/conversations/{conversation['id']}/messages",
            "POST",
            {"content": "searchable unique phrase", "artifact_ids": ["artifact-1"]},
        )
        self.assertEqual(status, 201)
        self.assertEqual(message["role"], "user")
        self.assertEqual(message["ordinal"], 1)

        query = urllib.parse.urlencode({"q": "unique phrase"})
        status, _, result = self.req(f"/api/v1/workspaces/conversations?{query}")
        self.assertEqual(status, 200)
        self.assertEqual([item["id"] for item in result["items"]], [conversation["id"]])

        status, _, messages = self.req(
            f"/api/v1/workspaces/conversations/{conversation['id']}/messages"
        )
        self.assertEqual(status, 200)
        self.assertEqual([item["id"] for item in messages["items"]], [message["id"]])

    def test_viewer_can_read_but_cannot_write(self):
        _, secret = self.auth.create_key("default", "workspace-viewer", "viewer", ["workspace:read"])
        status, _, result = self.req("/api/v1/workspaces/projects", token=secret)
        self.assertEqual(status, 200)
        self.assertEqual(result["items"], [])

        status, payload = self.error(
            "/api/v1/workspaces/projects",
            "POST",
            {"name": "Denied"},
            token=secret,
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["code"], "auth_failed")

    def test_delete_requires_admin_delete_scope(self):
        _, operator_secret = self.auth.create_key(
            "default", "workspace-operator", "operator", ["workspace:read", "workspace:write"]
        )
        _, _, conversation = self.req(
            "/api/v1/workspaces/conversations", "POST", {"title": "Delete access"}
        )
        status, payload = self.error(
            f"/api/v1/workspaces/conversations/{conversation['id']}/delete",
            "POST",
            {},
            token=operator_secret,
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["code"], "auth_failed")

        _, admin_secret = self.auth.create_key(
            "default", "workspace-admin", "admin", ["workspace:delete"]
        )
        status, _, deleted = self.req(
            f"/api/v1/workspaces/conversations/{conversation['id']}/delete",
            "POST",
            {},
            token=admin_secret,
        )
        self.assertEqual(status, 200)
        self.assertTrue(deleted["ok"])

    def test_external_api_rejects_assistant_role_and_audit_does_not_copy_message_content(self):
        _, _, conversation = self.req(
            "/api/v1/workspaces/conversations", "POST", {"title": "Role boundary"}
        )
        status, payload = self.error(
            f"/api/v1/workspaces/conversations/{conversation['id']}/messages",
            "POST",
            {"role": "assistant", "content": "must not inject assistant content"},
        )
        self.assertEqual(status, 400)
        self.assertIn("role=user only", payload["error"]["message"])

        secret_text = "audit-must-not-contain-this-message-body"
        self.req(
            f"/api/v1/workspaces/conversations/{conversation['id']}/messages",
            "POST",
            {"content": secret_text},
        )
        audit = self.db.list_audit("default", limit=20)
        message_events = [item for item in audit if item["action"] == "workspace.message.append"]
        self.assertEqual(len(message_events), 1)
        self.assertNotIn(secret_text, json.dumps(message_events[0], ensure_ascii=False))

    def test_cross_tenant_resource_is_not_visible(self):
        _, _, project = self.req(
            "/api/v1/workspaces/projects", "POST", {"name": "Default private project"}
        )
        self.req("/api/v1/tenants", "POST", {"id": "acme", "name": "Acme"})
        status, payload = self.error(
            f"/api/v1/workspaces/projects/{project['id']}",
            headers={"X-Tenant-ID": "acme"},
        )
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"]["code"], "workspace_project_not_found")

    def test_compliance_hold_delete_is_rejected(self):
        _, _, conversation = self.req(
            "/api/v1/workspaces/conversations",
            "POST",
            {"title": "Held", "retention_policy": "compliance_hold"},
        )
        status, payload = self.error(
            f"/api/v1/workspaces/conversations/{conversation['id']}/delete",
            "POST",
            {},
        )
        self.assertEqual(status, 400)
        self.assertIn("compliance hold", payload["error"]["message"])


if __name__ == "__main__":
    unittest.main()
