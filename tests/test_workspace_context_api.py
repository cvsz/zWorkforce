import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from tests.common import stack
from zworkforce.workspace_context_api import WorkspaceContextApp


class WorkspaceContextApiTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()
        self.app = WorkspaceContextApp(self.settings, self.db, self.engine, self.auth, self.provider)
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
        request = urllib.request.Request(self.base + path, data=data, headers=request_headers, method=method)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers), json.loads(response.read())

    def error(self, path, method="GET", body=None, headers=None, token="test-admin-secret"):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.req(path, method, body, headers, token)
        payload = json.loads(ctx.exception.read())
        return ctx.exception.code, payload

    def create_conversation_with_messages(self):
        _, _, conversation = self.req(
            "/api/v1/workspaces/conversations", "POST", {"title": "Context API"}
        )
        message_ids = []
        for content in ("first durable message", "second durable message"):
            _, _, message = self.req(
                f"/api/v1/workspaces/conversations/{conversation['id']}/messages",
                "POST",
                {"content": content},
            )
            message_ids.append(message["id"])
        return conversation, message_ids

    def test_snapshot_create_list_and_get(self):
        conversation, message_ids = self.create_conversation_with_messages()
        status, _, snapshot = self.req(
            f"/api/v1/workspaces/conversations/{conversation['id']}/context-snapshots",
            "POST",
            {
                "model_id": "test-model",
                "context_ceiling_tokens": 8192,
                "compaction_threshold_tokens": 6144,
                "message_ids": message_ids,
                "reason": "api-checkpoint",
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(snapshot["conversation_id"], conversation["id"])
        self.assertEqual([item["message_id"] for item in snapshot["members"]], message_ids)
        self.assertGreater(snapshot["estimated_tokens"], 0)

        status, _, listed = self.req(
            f"/api/v1/workspaces/conversations/{conversation['id']}/context-snapshots"
        )
        self.assertEqual(status, 200)
        self.assertEqual([item["id"] for item in listed["items"]], [snapshot["id"]])

        status, _, fetched = self.req(f"/api/v1/workspaces/context-snapshots/{snapshot['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched["id"], snapshot["id"])
        self.assertEqual(len(fetched["members"]), 2)

    def test_checkpoint_scope_cannot_create_summary_bearing_snapshot(self):
        conversation, message_ids = self.create_conversation_with_messages()
        _, write_only = self.auth.create_key(
            "default", "checkpoint-writer", "operator", ["workspace:read", "workspace:write"]
        )
        status, payload = self.error(
            f"/api/v1/workspaces/conversations/{conversation['id']}/context-snapshots",
            "POST",
            {
                "model_id": "test-model",
                "context_ceiling_tokens": 8192,
                "compaction_threshold_tokens": 4096,
                "message_ids": message_ids,
                "summary": "must require compact authority",
            },
            token=write_only,
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "invalid_request")
        self.assertIn("/compact", payload["error"]["message"])
        self.assertEqual(self.db.list_workspace_context_snapshots("default", conversation["id"]), [])

    def test_compact_requires_dedicated_scope_and_audit_redacts_summary(self):
        conversation, message_ids = self.create_conversation_with_messages()
        _, write_only = self.auth.create_key(
            "default", "workspace-writer", "operator", ["workspace:write", "workspace:read"]
        )
        compact_body = {
            "model_id": "test-model",
            "context_ceiling_tokens": 8192,
            "compaction_threshold_tokens": 4096,
            "message_ids": message_ids,
            "summary": "sensitive-summary-must-not-appear-in-audit",
        }
        status, payload = self.error(
            f"/api/v1/workspaces/conversations/{conversation['id']}/compact",
            "POST",
            compact_body,
            token=write_only,
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["code"], "auth_failed")

        _, compact_secret = self.auth.create_key(
            "default", "workspace-compactor", "operator", ["workspace:compact"]
        )
        status, _, snapshot = self.req(
            f"/api/v1/workspaces/conversations/{conversation['id']}/compact",
            "POST",
            compact_body,
            token=compact_secret,
        )
        self.assertEqual(status, 201)
        self.assertTrue(snapshot["summary_sha256"])
        self.assertEqual(snapshot["reason"], "manual-compact")

        audit = self.db.list_audit("default", limit=20)
        compact_events = [item for item in audit if item["action"] == "workspace.context.compact"]
        self.assertEqual(len(compact_events), 1)
        serialized = json.dumps(compact_events[0], ensure_ascii=False)
        self.assertNotIn(compact_body["summary"], serialized)
        self.assertIn(snapshot["summary_sha256"], serialized)

    def test_viewer_can_read_context_but_cannot_create_checkpoint(self):
        conversation, _ = self.create_conversation_with_messages()
        _, viewer_secret = self.auth.create_key("default", "context-viewer", "viewer", ["workspace:read"])
        status, _, listed = self.req(
            f"/api/v1/workspaces/conversations/{conversation['id']}/context-snapshots",
            token=viewer_secret,
        )
        self.assertEqual(status, 200)
        self.assertEqual(listed["items"], [])

        status, payload = self.error(
            f"/api/v1/workspaces/conversations/{conversation['id']}/context-snapshots",
            "POST",
            {
                "model_id": "test-model",
                "context_ceiling_tokens": 8192,
                "compaction_threshold_tokens": 4096,
            },
            token=viewer_secret,
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["code"], "auth_failed")

    def test_cross_tenant_snapshot_is_not_visible(self):
        conversation, _ = self.create_conversation_with_messages()
        _, _, snapshot = self.req(
            f"/api/v1/workspaces/conversations/{conversation['id']}/context-snapshots",
            "POST",
            {
                "model_id": "test-model",
                "context_ceiling_tokens": 8192,
                "compaction_threshold_tokens": 4096,
            },
        )
        self.req("/api/v1/tenants", "POST", {"id": "acme", "name": "Acme"})
        status, payload = self.error(
            f"/api/v1/workspaces/context-snapshots/{snapshot['id']}",
            headers={"X-Tenant-ID": "acme"},
        )
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"]["code"], "workspace_context_snapshot_not_found")


if __name__ == "__main__":
    unittest.main()
