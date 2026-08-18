import json
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

from tests.common import stack
from zworkforce.browser_effect_api import BrowserEffectApp

ACTION_A = "a" * 64
ACTION_B = "b" * 64
RESULT = "c" * 64


class BrowserEffectLifecycleApiTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()
        self.app = BrowserEffectApp(self.settings, self.db, self.engine, self.auth, self.provider)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.app.handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.admin_secret = "test-admin-secret"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.engine.shutdown()
        self.temp.cleanup()

    def req(self, path, method="GET", body=None, headers=None, token=None, timeout=10):
        token = token or self.admin_secret
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

    def error(self, path, method="GET", body=None, headers=None, token=None):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.req(path, method, body, headers, token)
        payload = json.loads(ctx.exception.read())
        return ctx.exception.code, payload

    def approved_task(self, prompt="browser effect approval"):
        task, created = self.engine.submit(
            "default",
            "software-engineer",
            prompt,
            actor="requester",
            mutating=True,
            idempotency_key=None,
            max_attempts=1,
        )
        self.assertTrue(created)
        self.assertEqual(task["status"], "waiting_approval")
        task = self.db.approval_decision("default", task["id"], "independent-reviewer", "approve")
        self.assertIsNotNone(task["approved_at"])
        return task

    def begin(self, approval, key="click-save-1", action=ACTION_A, tenant="default", token=None):
        return self.req(
            "/api/v1/browser-effects",
            "POST",
            {"idempotency_key": key, "action_sha256": action, "approval_task_id": approval["id"]},
            token=token,
        )

    def test_full_lifecycle_begin_claim_finish_and_read(self):
        approval = self.approved_task()
        status, _, effect = self.begin(approval)
        self.assertEqual(status, 201)
        self.assertEqual(effect["status"], "not_started")
        self.assertRegex(effect["id"], r"^[0-9A-Fa-f-]{36}$")

        read_status, _, fetched = self.req(f"/api/v1/browser-effects/{effect['id']}")
        self.assertEqual(read_status, 200)
        self.assertEqual(fetched["id"], effect["id"])
        self.assertEqual(fetched["status"], "not_started")

        claim_status, _, claimed = self.req(f"/api/v1/browser-effects/{effect['id']}/claim", "POST", {})
        self.assertEqual(claim_status, 200)
        self.assertTrue(claimed["claimed"])
        self.assertEqual(claimed["effect"]["status"], "executing")

        finish_status, _, finished = self.req(
            f"/api/v1/browser-effects/{effect['id']}/finish",
            "POST",
            {"status": "succeeded", "result_sha256": RESULT},
        )
        self.assertEqual(finish_status, 200)
        self.assertEqual(finished["status"], "succeeded")
        self.assertEqual(finished["result_sha256"], RESULT)

        read_status, _, done = self.req(f"/api/v1/browser-effects/{effect['id']}")
        self.assertEqual(read_status, 200)
        self.assertEqual(done["status"], "succeeded")

        second_claim_status, _, second_claim = self.req(
            f"/api/v1/browser-effects/{effect['id']}/claim", "POST", {}
        )
        self.assertEqual(second_claim_status, 200)
        self.assertFalse(second_claim["claimed"])
        self.assertEqual(second_claim["effect"]["status"], "succeeded")

    def test_begin_replay_is_deduplicated_and_returns_stored_result(self):
        approval = self.approved_task("dedup lifecycle")
        status, _, effect = self.begin(approval)
        self.assertEqual(status, 201)
        _, _, claimed = self.req(f"/api/v1/browser-effects/{effect['id']}/claim", "POST", {})
        self.assertTrue(claimed["claimed"])
        _, _, finished = self.req(
            f"/api/v1/browser-effects/{effect['id']}/finish",
            "POST",
            {"status": "succeeded", "result_sha256": RESULT},
        )
        self.assertEqual(finished["status"], "succeeded")

        replay_status, _, replay = self.begin(approval)
        self.assertEqual(replay_status, 200)
        self.assertEqual(replay["id"], effect["id"])
        self.assertEqual(replay["status"], "succeeded")
        self.assertEqual(replay["result_sha256"], RESULT)

    def test_unknown_effect_never_reclaims_and_requires_admin_reconciliation(self):
        approval = self.approved_task("unknown lifecycle")
        _, _, effect = self.begin(approval, key="unknown-1")
        _, _, claimed = self.req(f"/api/v1/browser-effects/{effect['id']}/claim", "POST", {})
        self.assertTrue(claimed["claimed"])
        _, _, unknown = self.req(
            f"/api/v1/browser-effects/{effect['id']}/finish",
            "POST",
            {"status": "unknown", "error_code": "transport_lost"},
        )
        self.assertEqual(unknown["status"], "unknown")

        _, _, replay_claim = self.req(f"/api/v1/browser-effects/{effect['id']}/claim", "POST", {})
        self.assertFalse(replay_claim["claimed"])
        self.assertEqual(replay_claim["effect"]["status"], "unknown")

        _, operator_secret = self.auth.create_key(
            "default", "effect-operator", "operator", ["task:write"]
        )
        op_status, op_payload = self.error(
            f"/api/v1/browser-effects/{effect['id']}/reconcile",
            "POST",
            {"status": "succeeded", "result_sha256": RESULT},
            token=operator_secret,
        )
        self.assertEqual(op_status, 403)

        _, admin_secret = self.auth.create_key(
            "default", "effect-admin", "admin", ["task:write", "workforce:read"]
        )
        reconcile_status, _, reconciled = self.req(
            f"/api/v1/browser-effects/{effect['id']}/reconcile",
            "POST",
            {"status": "succeeded", "result_sha256": RESULT},
            token=admin_secret,
        )
        self.assertEqual(reconcile_status, 200)
        self.assertEqual(reconciled["status"], "succeeded")
        self.assertEqual(reconciled["result_sha256"], RESULT)

        repeat_status, repeat_payload = self.error(
            f"/api/v1/browser-effects/{effect['id']}/reconcile",
            "POST",
            {"status": "failed"},
            token=admin_secret,
        )
        self.assertEqual(repeat_status, 400)
        self.assertIn("only unknown", repeat_payload["error"]["message"])

    def test_canceled_approval_blocks_claim(self):
        approval = self.approved_task("cancel fence")
        _, _, effect = self.begin(approval, key="cancel-1")
        self.db.update_task(approval["id"], cancel_requested=1, status="canceled")
        status, _, claimed = self.req(f"/api/v1/browser-effects/{effect['id']}/claim", "POST", {})
        self.assertEqual(status, 200)
        self.assertFalse(claimed["claimed"])
        self.assertEqual(claimed["effect"]["status"], "not_started")

    def test_begin_rejects_unapproved_or_cross_tenant_approval(self):
        task, _ = self.engine.submit(
            "default",
            "software-engineer",
            "unapproved mutation",
            actor="requester-two",
            mutating=True,
            idempotency_key=None,
            max_attempts=1,
        )
        status, payload = self.error(
            "/api/v1/browser-effects",
            "POST",
            {"idempotency_key": "unapproved-1", "action_sha256": ACTION_A, "approval_task_id": task["id"]},
        )
        self.assertEqual(status, 400)
        self.assertIn("approved tenant mutation", payload["error"]["message"])

        approval = self.approved_task("cross tenant")
        self.db.ensure_tenant("acme", "Acme")
        _, acme_secret = self.auth.create_key(
            "acme", "acme-admin", "admin", ["task:write", "workforce:read"]
        )
        status, payload = self.error(
            "/api/v1/browser-effects",
            "POST",
            {"idempotency_key": "cross-1", "action_sha256": ACTION_A, "approval_task_id": approval["id"]},
            token=acme_secret,
        )
        self.assertEqual(status, 400)
        self.assertIn("approved tenant mutation", payload["error"]["message"])

    def test_cross_tenant_effect_read_is_denied(self):
        approval = self.approved_task("tenant read isolation")
        _, _, effect = self.begin(approval, key="tenant-read-1")
        self.db.ensure_tenant("acme", "Acme")
        _, acme_secret = self.auth.create_key(
            "acme", "acme-admin", "admin", ["task:write", "workforce:read"]
        )
        status, payload = self.error(
            f"/api/v1/browser-effects/{effect['id']}", token=acme_secret
        )
        self.assertEqual(status, 404)
        self.assertIn("not found", payload["error"]["message"])

    def test_finish_and_reconcile_validate_status_and_digest(self):
        approval = self.approved_task("terminal validation")
        _, _, effect = self.begin(approval, key="validate-1")
        _, _, claimed = self.req(f"/api/v1/browser-effects/{effect['id']}/claim", "POST", {})
        self.assertTrue(claimed["claimed"])

        status, payload = self.error(
            f"/api/v1/browser-effects/{effect['id']}/finish",
            "POST",
            {"status": "invalid"},
        )
        self.assertEqual(status, 400)
        self.assertIn("terminal status", payload["error"]["message"])

        status, payload = self.error(
            f"/api/v1/browser-effects/{effect['id']}/finish",
            "POST",
            {"status": "succeeded", "result_sha256": "not-a-digest"},
        )
        self.assertEqual(status, 400)
        self.assertIn("digest", payload["error"]["message"])

        cancel_status, _, canceled = self.req(
            f"/api/v1/browser-effects/{effect['id']}/finish",
            "POST",
            {"status": "canceled"},
        )
        self.assertEqual(cancel_status, 200)
        self.assertEqual(canceled["status"], "canceled")

        replay_status, _, replay_claim = self.req(
            f"/api/v1/browser-effects/{effect['id']}/claim", "POST", {}
        )
        self.assertEqual(replay_status, 200)
        self.assertFalse(replay_claim["claimed"])
        self.assertEqual(replay_claim["effect"]["status"], "canceled")

    def test_operator_can_begin_claim_and_finish_but_not_reconcile(self):
        approval = self.approved_task("operator lifecycle")
        _, operator_secret = self.auth.create_key(
            "default", "effect-operator-2", "operator", ["task:write"]
        )
        status, _, effect = self.begin(approval, key="operator-1", token=operator_secret)
        self.assertEqual(status, 201)
        _, _, claimed = self.req(
            f"/api/v1/browser-effects/{effect['id']}/claim", "POST", {}, token=operator_secret
        )
        self.assertTrue(claimed["claimed"])
        _, _, finished = self.req(
            f"/api/v1/browser-effects/{effect['id']}/finish",
            "POST",
            {"status": "failed", "error_code": "site_denied"},
            token=operator_secret,
        )
        self.assertEqual(finished["status"], "failed")
        self.assertEqual(finished["error_code"], "site_denied")

        status, payload = self.error(
            f"/api/v1/browser-effects/{effect['id']}/finish",
            "POST",
            {"status": "unknown"},
            token=operator_secret,
        )
        self.assertEqual(status, 400)
        self.assertIn("not executing", payload["error"]["message"])


if __name__ == "__main__":
    unittest.main()