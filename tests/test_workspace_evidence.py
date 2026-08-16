import json
import threading
import unittest
import urllib.error
import urllib.request
import uuid
from http.server import ThreadingHTTPServer

from tests.common import stack
from zworkforce.workspace_evidence_api import WorkspaceEvidenceApp


class WorkspaceEvidenceApiTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()
        self.app = WorkspaceEvidenceApp(self.settings, self.db, self.engine, self.auth, self.provider)
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
            return response.status, json.loads(response.read())

    def error(self, path, token="test-admin-secret", headers=None):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.req(path, headers=headers, token=token)
        return ctx.exception.code, json.loads(ctx.exception.read())

    def create_task(self):
        status, task = self.req(
            "/api/v1/tasks",
            "POST",
            {
                "agent_id": "software-engineer",
                "prompt": "PROMPT-SECRET must never appear in the sidecar",
                "mutating": False,
            },
        )
        self.assertEqual(status, 201)
        return task

    def add_projection_evidence(self, task):
        self.db.update_task(task["id"], result="RESULT-SECRET", cost_credits=1.25, input_tokens=20, output_tokens=10)
        self.db.task_event(
            "default",
            task["id"],
            "diagnostic",
            "tester",
            {"raw": "EVENT-DETAIL-SECRET"},
        )
        self.db.record_tool_event(
            "default",
            task["id"],
            task["agent_id"],
            "http_get",
            False,
            True,
            12.5,
            {"Authorization": "Bearer TOOL-SECRET", "query": "QUERY-SECRET", "nested": {"token": "NESTED-SECRET"}},
        )
        self.db.register_artifact(
            "default",
            {
                "name": "report.md",
                "content_type": "text/markdown",
                "storage_uri": "file:///sensitive/STORAGE-SECRET/report.md",
                "sha256": "a" * 64,
                "size_bytes": 42,
                "task_id": task["id"],
                "metadata": {"token": "ARTIFACT-SECRET", "project": "private-project"},
            },
            "tester",
        )
        child = {
            "id": str(uuid.uuid4()),
            "tenant_id": "default",
            "agent_id": "software-engineer",
            "prompt": "CHILD-PROMPT-SECRET",
            "created_by": "tester",
            "status": "queued",
            "tier": "terra",
            "model": "mock-terra",
            "provider_name": "mock",
            "mutating": False,
            "parent_task_id": task["id"],
            "depth": 1,
            "required_approvals": 0,
            "priority": 0,
            "max_attempts": 3,
            "success_criteria": [],
        }
        self.db.create_task(child)

        workflow = self.db.upsert_workflow(
            "default",
            {
                "id": "evidence-sidecar",
                "name": "Evidence Sidecar",
                "definition": {"steps": [{"id": "inspect", "agent_id": "software-engineer", "prompt": "WORKFLOW-PROMPT-SECRET"}]},
            },
            "tester",
        )
        run = self.db.create_workflow_run("default", workflow, "tester", {"secret": "WORKFLOW-INPUT-SECRET"})
        self.db.update_workflow_step(run["id"], "inspect", status="running", task_id=task["id"])

    def test_sidecar_projects_durable_evidence_without_raw_sensitive_payloads(self):
        task = self.create_task()
        self.add_projection_evidence(task)

        status, payload = self.req(f"/api/v1/tasks/{task['id']}/sidecar")
        self.assertEqual(status, 200)
        self.assertEqual(payload["task"]["id"], task["id"])
        self.assertTrue(payload["task"]["has_result"])
        self.assertEqual(payload["counts"]["artifacts"], 1)
        self.assertEqual(payload["counts"]["subtasks"], 1)
        self.assertEqual(payload["counts"]["workflow_refs"], 1)
        self.assertEqual(payload["artifacts"][0]["sha256"], "a" * 64)
        self.assertNotIn("storage_uri", payload["artifacts"][0])
        self.assertEqual(payload["tool_calls"][0]["argument_shape"]["Authorization"]["type"], "redacted")
        self.assertEqual(payload["tool_calls"][0]["argument_shape"]["nested"]["token"]["type"], "redacted")
        self.assertEqual(payload["tool_calls"][0]["argument_shape"]["query"]["type"], "string")

        serialized = json.dumps(payload, ensure_ascii=False)
        for secret in (
            "PROMPT-SECRET",
            "RESULT-SECRET",
            "EVENT-DETAIL-SECRET",
            "TOOL-SECRET",
            "QUERY-SECRET",
            "NESTED-SECRET",
            "STORAGE-SECRET",
            "ARTIFACT-SECRET",
            "private-project",
            "CHILD-PROMPT-SECRET",
            "WORKFLOW-PROMPT-SECRET",
            "WORKFLOW-INPUT-SECRET",
        ):
            self.assertNotIn(secret, serialized)

    def test_sidecar_is_tenant_scoped_and_requires_workforce_read(self):
        task = self.create_task()
        _, viewer = self.auth.create_key("default", "sidecar-viewer", "viewer", ["workforce:read"])
        status, payload = self.req(f"/api/v1/tasks/{task['id']}/sidecar", token=viewer)
        self.assertEqual(status, 200)
        self.assertEqual(payload["task"]["id"], task["id"])

        _, no_read = self.auth.create_key("default", "no-workforce-read", "viewer", ["workspace:read"])
        status, payload = self.error(f"/api/v1/tasks/{task['id']}/sidecar", token=no_read)
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["code"], "auth_failed")

        self.req("/api/v1/tenants", "POST", {"id": "acme", "name": "Acme"})
        status, payload = self.error(
            f"/api/v1/tasks/{task['id']}/sidecar",
            headers={"X-Tenant-ID": "acme"},
        )
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"]["code"], "task_not_found")


if __name__ == "__main__":
    unittest.main()
