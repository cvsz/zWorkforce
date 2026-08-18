import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

ZIDER_ROOT = Path(__file__).resolve().parent.parent
if str(ZIDER_ROOT) not in sys.path:
    sys.path.insert(0, str(ZIDER_ROOT))

import app.services.zworkforce_bridge as bridge_module
from app.services.zworkforce_bridge import ZWorkforceBridge, ZWorkforceBridgeError


class FakeResponse:
    def __init__(self, status_code=200, payload=None, json_error=None):
        self.status_code = status_code
        self.payload = payload if payload is not None else {}
        self.json_error = json_error

    def json(self):
        if self.json_error is not None:
            raise self.json_error
        return self.payload


class FakeClient:
    def __init__(self, *, get_result=None, post_result=None, get_error=None, post_error=None):
        self.get_result = get_result
        self.post_result = post_result
        self.get_error = get_error
        self.post_error = post_error
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, **kwargs):
        self.requests.append(("GET", url, kwargs))
        if self.get_error is not None:
            raise self.get_error
        return self.get_result

    async def post(self, url, **kwargs):
        self.requests.append(("POST", url, kwargs))
        if self.post_error is not None:
            raise self.post_error
        return self.post_result


class ZWorkforceBridgeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.old_url = ZWorkforceBridge.ZWF_URL
        self.old_token = ZWorkforceBridge.ZWF_TOKEN
        ZWorkforceBridge.ZWF_URL = "https://zwf.example.test"
        ZWorkforceBridge.ZWF_TOKEN = "super-secret-token"

    def tearDown(self):
        ZWorkforceBridge.ZWF_URL = self.old_url
        ZWorkforceBridge.ZWF_TOKEN = self.old_token

    async def test_overview_returns_only_real_upstream_payload(self):
        client = FakeClient(get_result=FakeResponse(payload={"status": "healthy", "active_tasks": 2}))
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=client):
            result = await ZWorkforceBridge.get_overview()
        self.assertEqual(result, {"status": "healthy", "active_tasks": 2})
        self.assertEqual(client.requests[0][2]["headers"]["Authorization"], "Bearer super-secret-token")

    async def test_network_failure_does_not_fabricate_connected_state(self):
        request = httpx.Request("GET", "https://zwf.example.test/api/v1/overview")
        client = FakeClient(get_error=httpx.ReadTimeout("timeout", request=request))
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=client):
            with self.assertRaisesRegex(ZWorkforceBridgeError, "unavailable") as ctx:
                await ZWorkforceBridge.get_overview()
        self.assertEqual(ctx.exception.status_code, 503)

    async def test_dispatch_forwards_control_plane_contract_and_idempotency_key(self):
        client = FakeClient(post_result=FakeResponse(payload={"id": "task-1", "state": "queued"}))
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=client):
            result = await ZWorkforceBridge.dispatch_task(
                "title",
                "prompt",
                "general",
                idempotency_key="zider-dispatch-42",
            )
        self.assertEqual(result["id"], "task-1")
        method, url, request = client.requests[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://zwf.example.test/api/v1/tasks")
        self.assertEqual(request["json"], {"agent_id": "general", "prompt": "prompt"})
        headers = request["headers"]
        self.assertEqual(headers["Idempotency-Key"], "zider-dispatch-42")
        self.assertEqual(headers["Authorization"], "Bearer super-secret-token")

    async def test_dispatch_rejects_missing_or_header_unsafe_idempotency_key_before_transport(self):
        client = FakeClient(post_result=FakeResponse(payload={"id": "unexpected"}))
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=client):
            for key in ("", "bad key", "bad\nkey", "x" * 129):
                with self.subTest(key=repr(key)):
                    with self.assertRaisesRegex(ZWorkforceBridgeError, "idempotency key") as ctx:
                        await ZWorkforceBridge.dispatch_task(
                            "title",
                            "prompt",
                            "general",
                            idempotency_key=key,
                        )
                    self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(client.requests, [])

    async def test_dispatch_failure_does_not_fabricate_queued_task_or_reflect_body(self):
        client = FakeClient(
            post_result=FakeResponse(
                status_code=500,
                payload={"detail": "database failed: token=upstream-secret"},
            )
        )
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=client):
            with self.assertRaises(ZWorkforceBridgeError) as ctx:
                await ZWorkforceBridge.dispatch_task(
                    "title",
                    "prompt",
                    "general",
                    idempotency_key="failure-case-1",
                )
        message = str(ctx.exception)
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("upstream status 500", message)
        self.assertNotIn("upstream-secret", message)
        self.assertNotIn("queued", message)

    async def test_auth_failure_is_bounded_and_does_not_reflect_credentials(self):
        client = FakeClient(get_result=FakeResponse(status_code=401, payload={"token": "leaked"}))
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=client):
            with self.assertRaises(ZWorkforceBridgeError) as ctx:
                await ZWorkforceBridge.get_overview()
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("authentication was rejected", str(ctx.exception))
        self.assertNotIn("super-secret-token", str(ctx.exception))
        self.assertNotIn("leaked", str(ctx.exception))

    async def test_invalid_json_and_non_object_payload_fail_closed(self):
        invalid_json = FakeClient(get_result=FakeResponse(json_error=ValueError("bad json")))
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=invalid_json):
            with self.assertRaisesRegex(ZWorkforceBridgeError, "invalid JSON") as ctx:
                await ZWorkforceBridge.get_overview()
        self.assertEqual(ctx.exception.status_code, 502)

        non_object = FakeClient(get_result=FakeResponse(payload=["unexpected"]))
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=non_object):
            with self.assertRaisesRegex(ZWorkforceBridgeError, "response shape"):
                await ZWorkforceBridge.get_overview()

    async def test_remote_http_control_plane_is_rejected_before_token_transport(self):
        ZWorkforceBridge.ZWF_URL = "http://zwf.example.test"
        client = FakeClient(get_result=FakeResponse(payload={"status": "healthy"}))
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=client):
            with self.assertRaisesRegex(ZWorkforceBridgeError, "HTTPS outside loopback"):
                await ZWorkforceBridge.get_overview()
        self.assertEqual(client.requests, [])

    async def test_loopback_http_remains_supported_for_local_development(self):
        ZWorkforceBridge.ZWF_URL = "http://127.0.0.1:8000"
        client = FakeClient(get_result=FakeResponse(payload={"status": "healthy"}))
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=client):
            result = await ZWorkforceBridge.get_overview()
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(client.requests[0][1], "http://127.0.0.1:8000/api/v1/overview")

    async def test_browser_approval_request_uses_mutating_task_and_bounded_idempotency(self):
        client = FakeClient(
            post_result=FakeResponse(
                payload={"id": "123e4567-e89b-12d3-a456-426614174000", "status": "waiting_approval", "required_approvals": 1}
            )
        )
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=client):
            result = await ZWorkforceBridge.request_browser_approval(
                agent_id="browser-review",
                prompt="zider-browser-approval:v1 {}",
                idempotency_key="browser-approval:action-42",
            )
        self.assertEqual(result["status"], "waiting_approval")
        method, url, request = client.requests[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://zwf.example.test/api/v1/tasks")
        self.assertEqual(
            request["json"],
            {
                "agent_id": "browser-review",
                "prompt": "zider-browser-approval:v1 {}",
                "mutating": True,
                "max_attempts": 1,
            },
        )
        self.assertEqual(request["headers"]["Idempotency-Key"], "browser-approval:action-42")

    async def test_browser_approval_lookup_and_cancel_use_existing_task_authority(self):
        task_id = "123e4567-e89b-12d3-a456-426614174000"
        lookup = FakeClient(get_result=FakeResponse(payload={"id": task_id, "status": "queued", "approved_at": "now"}))
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=lookup):
            result = await ZWorkforceBridge.get_task(task_id)
        self.assertEqual(result["id"], task_id)
        self.assertEqual(lookup.requests[0][1], f"https://zwf.example.test/api/v1/tasks/{task_id}")

        approvals = FakeClient(get_result=FakeResponse(payload={"items": [{"actor": "reviewer", "decision": "approve"}]}))
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=approvals):
            items = await ZWorkforceBridge.get_task_approvals(task_id)
        self.assertEqual(items[0]["decision"], "approve")
        self.assertEqual(approvals.requests[0][1], f"https://zwf.example.test/api/v1/tasks/{task_id}/approvals")

        cancel = FakeClient(post_result=FakeResponse(payload={"id": task_id, "status": "canceled"}))
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=cancel):
            canceled = await ZWorkforceBridge.cancel_task(task_id)
        self.assertEqual(canceled["status"], "canceled")
        self.assertEqual(cancel.requests[0][1], f"https://zwf.example.test/api/v1/tasks/{task_id}/cancel")

    async def test_approval_lookup_rejects_invalid_shape_and_task_ids_before_transport(self):
        bad_shape = FakeClient(get_result=FakeResponse(payload={"items": "not-a-list"}))
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=bad_shape):
            with self.assertRaisesRegex(ZWorkforceBridgeError, "response shape"):
                await ZWorkforceBridge.get_task_approvals("123e4567-e89b-12d3-a456-426614174000")

        client = FakeClient(get_result=FakeResponse(payload={"unexpected": True}))
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=client):
            with self.assertRaisesRegex(ZWorkforceBridgeError, "task id is invalid"):
                await ZWorkforceBridge.get_task("../other-tenant")
        self.assertEqual(client.requests, [])


if __name__ == "__main__":
    unittest.main()