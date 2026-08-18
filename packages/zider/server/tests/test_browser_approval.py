import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ZIDER_ROOT = Path(__file__).resolve().parent.parent
if str(ZIDER_ROOT) not in sys.path:
    sys.path.insert(0, str(ZIDER_ROOT))

from app.services.agent_runner import BrowserAction
from app.services.browser_approval import ZWorkforceMutationApprovalAdapter, browser_action_binding
from app.services.zworkforce_bridge import ZWorkforceBridgeError


TASK_ID = "123e4567-e89b-12d3-a456-426614174000"
NOW = datetime(2026, 8, 18, 0, 0, 0, tzinfo=timezone.utc)


def action(**overrides):
    values = {
        "kind": "submit",
        "url": "https://example.com/account?csrf=secret#fragment",
        "selector": "form#profile",
        "value": "sensitive-form-value",
        "artifact_id": "",
        "idempotency_key": "browser-action-42",
        "resolved_addresses": ("93.184.216.34",),
    }
    values.update(overrides)
    return BrowserAction(**values)


class FakeBridge:
    task = {}
    approvals = []
    requested = []
    canceled = []
    fail_lookup = False

    @classmethod
    def reset(cls):
        cls.task = {}
        cls.approvals = []
        cls.requested = []
        cls.canceled = []
        cls.fail_lookup = False

    @classmethod
    async def request_browser_approval(cls, *, agent_id, prompt, idempotency_key):
        cls.requested.append((agent_id, prompt, idempotency_key))
        return dict(cls.task)

    @classmethod
    async def get_task(cls, task_id):
        if cls.fail_lookup:
            raise ZWorkforceBridgeError("unavailable")
        if task_id != TASK_ID:
            raise ZWorkforceBridgeError("not found", status_code=404)
        return dict(cls.task)

    @classmethod
    async def get_task_approvals(cls, task_id):
        if cls.fail_lookup:
            raise ZWorkforceBridgeError("unavailable")
        return [dict(item) for item in cls.approvals]

    @classmethod
    async def cancel_task(cls, task_id):
        cls.canceled.append(task_id)
        return {"id": task_id, "status": "canceled"}


class BrowserApprovalAdapterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeBridge.reset()
        self.adapter = ZWorkforceMutationApprovalAdapter(
            bridge=FakeBridge,
            ttl_seconds=600,
            now=lambda: NOW,
        )

    def approved_task(self, browser_action):
        envelope = self.adapter.envelope(browser_action)
        FakeBridge.task = {
            "id": TASK_ID,
            "tenant_id": "tenant-a",
            "created_by": "zider-service",
            "prompt": envelope.prompt(),
            "status": "queued",
            "mutating": True,
            "required_approvals": 1,
            "approved_at": "2026-08-18T00:01:00+00:00",
            "cancel_requested": 0,
        }
        FakeBridge.approvals = [
            {"actor": "independent-reviewer", "decision": "approve"},
        ]

    async def test_exact_durable_approval_authorizes_matching_action(self):
        browser_action = action()
        self.approved_task(browser_action)

        self.assertTrue(await self.adapter.authorize(browser_action, TASK_ID))

    async def test_action_binding_does_not_store_secret_inputs(self):
        browser_action = action()
        envelope = self.adapter.envelope(browser_action)
        prompt = envelope.prompt()

        self.assertEqual(len(browser_action_binding(browser_action)), 64)
        self.assertIn("https://example.com/account", prompt)
        self.assertNotIn("csrf=secret", prompt)
        self.assertNotIn("sensitive-form-value", prompt)
        self.assertNotIn("form#profile", prompt)

    async def test_mismatched_action_cannot_reuse_approval(self):
        browser_action = action()
        self.approved_task(browser_action)

        changed = action(selector="button#delete")
        self.assertFalse(await self.adapter.authorize(changed, TASK_ID))

    async def test_unapproved_rejected_canceled_or_expired_task_fails_closed(self):
        browser_action = action()
        self.approved_task(browser_action)

        FakeBridge.task["status"] = "waiting_approval"
        FakeBridge.task["approved_at"] = None
        self.assertFalse(await self.adapter.authorize(browser_action, TASK_ID))

        self.approved_task(browser_action)
        FakeBridge.approvals = [{"actor": "reviewer", "decision": "reject"}]
        self.assertFalse(await self.adapter.authorize(browser_action, TASK_ID))

        self.approved_task(browser_action)
        FakeBridge.task["cancel_requested"] = 1
        self.assertFalse(await self.adapter.authorize(browser_action, TASK_ID))

        expired_adapter = ZWorkforceMutationApprovalAdapter(
            bridge=FakeBridge,
            ttl_seconds=60,
            now=lambda: datetime(2026, 8, 18, 1, 0, 0, tzinfo=timezone.utc),
        )
        self.assertFalse(await expired_adapter.authorize(browser_action, TASK_ID))

    async def test_lookup_failure_or_invalid_token_fails_closed(self):
        browser_action = action()
        self.approved_task(browser_action)
        FakeBridge.fail_lookup = True

        self.assertFalse(await self.adapter.authorize(browser_action, TASK_ID))
        self.assertFalse(await self.adapter.authorize(browser_action, "not-a-task-id"))

    async def test_request_requires_control_plane_waiting_approval(self):
        browser_action = action()
        envelope = self.adapter.envelope(browser_action)
        FakeBridge.task = {
            "id": TASK_ID,
            "status": "waiting_approval",
            "required_approvals": 1,
            "prompt": envelope.prompt(),
        }

        result = await self.adapter.request(browser_action, agent_id="browser-review")
        self.assertEqual(result["id"], TASK_ID)
        self.assertEqual(FakeBridge.requested[0][0], "browser-review")
        self.assertEqual(FakeBridge.requested[0][2], "browser-approval:browser-action-42")
        self.assertEqual(FakeBridge.canceled, [])

    async def test_misconfigured_approval_agent_is_canceled_and_rejected(self):
        browser_action = action()
        FakeBridge.task = {
            "id": TASK_ID,
            "status": "queued",
            "required_approvals": 0,
        }

        with self.assertRaisesRegex(ZWorkforceBridgeError, "does not enforce mutation approval"):
            await self.adapter.request(browser_action, agent_id="unsafe-agent")
        self.assertEqual(FakeBridge.canceled, [TASK_ID])


if __name__ == "__main__":
    unittest.main()
