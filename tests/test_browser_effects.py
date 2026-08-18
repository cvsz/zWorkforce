import unittest

from tests.common import stack
from zworkforce.db import SCHEMA_VERSION


ACTION_A = "a" * 64
ACTION_B = "b" * 64
RESULT = "c" * 64


class BrowserEffectLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()

    def tearDown(self):
        self.engine.shutdown()
        self.temp.cleanup()

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

    def test_schema_v8_and_exactly_once_claim(self):
        self.assertEqual(SCHEMA_VERSION, 8)
        approval = self.approved_task()
        effect = self.db.begin_browser_effect(
            "default",
            idempotency_key="click-save-1",
            action_sha256=ACTION_A,
            approval_task_id=approval["id"],
        )
        replay = self.db.begin_browser_effect(
            "default",
            idempotency_key="click-save-1",
            action_sha256=ACTION_A,
            approval_task_id=approval["id"],
        )
        self.assertEqual(replay["id"], effect["id"])

        claimed, should_execute = self.db.claim_browser_effect("default", effect["id"])
        self.assertTrue(should_execute)
        self.assertEqual(claimed["status"], "executing")

        claimed_again, should_execute_again = self.db.claim_browser_effect("default", effect["id"])
        self.assertFalse(should_execute_again)
        self.assertEqual(claimed_again["status"], "executing")

        done = self.db.finish_browser_effect(
            "default", effect["id"], status="succeeded", result_sha256=RESULT
        )
        self.assertEqual(done["status"], "succeeded")
        self.assertEqual(done["result_sha256"], RESULT)
        replay_done, execute_done = self.db.claim_browser_effect("default", effect["id"])
        self.assertFalse(execute_done)
        self.assertEqual(replay_done["status"], "succeeded")

    def test_idempotency_and_approval_binding_fail_closed(self):
        approval = self.approved_task()
        self.db.begin_browser_effect(
            "default",
            idempotency_key="submit-1",
            action_sha256=ACTION_A,
            approval_task_id=approval["id"],
        )
        with self.assertRaisesRegex(ValueError, "different approved action"):
            self.db.begin_browser_effect(
                "default",
                idempotency_key="submit-1",
                action_sha256=ACTION_B,
                approval_task_id=approval["id"],
            )
        with self.assertRaisesRegex(ValueError, "already bound"):
            self.db.begin_browser_effect(
                "default",
                idempotency_key="submit-2",
                action_sha256=ACTION_A,
                approval_task_id=approval["id"],
            )

    def test_unknown_requires_explicit_reconciliation_and_never_reclaims(self):
        approval = self.approved_task("unknown action")
        effect = self.db.begin_browser_effect(
            "default",
            idempotency_key="submit-unknown-1",
            action_sha256=ACTION_A,
            approval_task_id=approval["id"],
        )
        _, should_execute = self.db.claim_browser_effect("default", effect["id"])
        self.assertTrue(should_execute)
        unknown = self.db.finish_browser_effect(
            "default", effect["id"], status="unknown", error_code="transport_lost"
        )
        self.assertEqual(unknown["status"], "unknown")
        replay, should_replay = self.db.claim_browser_effect("default", effect["id"])
        self.assertFalse(should_replay)
        self.assertEqual(replay["status"], "unknown")

        reconciled = self.db.reconcile_browser_effect(
            "default", effect["id"], status="succeeded", result_sha256=RESULT
        )
        self.assertEqual(reconciled["status"], "succeeded")
        with self.assertRaisesRegex(ValueError, "only unknown"):
            self.db.reconcile_browser_effect("default", effect["id"], status="failed")

    def test_tenant_and_approval_state_are_enforced(self):
        approval = self.approved_task("tenant isolation")
        self.db.ensure_tenant("acme", "Acme")
        with self.assertRaisesRegex(ValueError, "approved tenant mutation"):
            self.db.begin_browser_effect(
                "acme",
                idempotency_key="cross-tenant-1",
                action_sha256=ACTION_A,
                approval_task_id=approval["id"],
            )

        task, _ = self.engine.submit(
            "default",
            "software-engineer",
            "still waiting",
            actor="requester-two",
            mutating=True,
            idempotency_key=None,
            max_attempts=1,
        )
        with self.assertRaisesRegex(ValueError, "approved tenant mutation"):
            self.db.begin_browser_effect(
                "default",
                idempotency_key="unapproved-1",
                action_sha256=ACTION_A,
                approval_task_id=task["id"],
            )


if __name__ == "__main__":
    unittest.main()
