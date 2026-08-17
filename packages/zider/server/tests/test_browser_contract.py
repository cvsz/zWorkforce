import asyncio
import sys
import unittest
from pathlib import Path

ZIDER_ROOT = Path(__file__).resolve().parent.parent
if str(ZIDER_ROOT) not in sys.path:
    sys.path.insert(0, str(ZIDER_ROOT))

from app.services.agent_runner import (
    AgentRunner,
    BrowserApprovalRequired,
    BrowserAutomationUnavailable,
    BrowserPolicyError,
)


class FakeExecutor:
    enforces_resolved_addresses = True

    def __init__(self):
        self.actions = []

    async def execute(self, action):
        self.actions.append(action)
        return {"ok": True, "kind": action.kind}


class UnpinnedExecutor:
    def __init__(self):
        self.actions = []

    async def execute(self, action):
        self.actions.append(action)
        return {"ok": True}


class BrowserContractTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        AgentRunner.reset()

    async def test_missing_executor_fails_closed_instead_of_fake_success(self):
        AgentRunner.configure(allowed_hosts=["example.com"], resolver=lambda host: ["93.184.216.34"])
        with self.assertRaises(BrowserAutomationUnavailable):
            await AgentRunner.run_claw_task(
                "Inspect the page",
                "test-model",
                actions=[{"kind": "inspect", "url": "https://example.com/page"}],
            )

    async def test_unpinned_executor_fails_closed_before_navigation(self):
        executor = UnpinnedExecutor()
        AgentRunner.configure(
            executor=executor,
            allowed_hosts=["example.com"],
            resolver=lambda host: ["93.184.216.34"],
        )
        with self.assertRaisesRegex(BrowserAutomationUnavailable, "resolved addresses"):
            await AgentRunner.run_claw_task(
                "Inspect the page",
                "test-model",
                actions=[{"kind": "inspect", "url": "https://example.com/page"}],
            )
        self.assertEqual(executor.actions, [])

    async def test_read_only_action_executes_without_mutation_approval(self):
        executor = FakeExecutor()
        AgentRunner.configure(
            executor=executor,
            allowed_hosts=["example.com"],
            resolver=lambda host: ["93.184.216.34"],
        )
        result = await AgentRunner.run_claw_task(
            "Inspect the page",
            "test-model",
            actions=[{"kind": "inspect", "url": "https://docs.example.com/page", "selector": "main"}],
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["steps"][0]["kind"], "inspect")
        self.assertFalse(result["steps"][0]["mutating"])
        self.assertEqual(len(executor.actions), 1)
        self.assertEqual(executor.actions[0].resolved_addresses, ("93.184.216.34",))

    async def test_mutating_action_requires_control_plane_approval(self):
        executor = FakeExecutor()
        AgentRunner.configure(
            executor=executor,
            allowed_hosts=["example.com"],
            resolver=lambda host: ["93.184.216.34"],
        )
        with self.assertRaises(BrowserApprovalRequired):
            await AgentRunner.run_claw_task(
                "Submit the approved form",
                "test-model",
                actions=[{
                    "kind": "submit",
                    "url": "https://example.com/form",
                    "selector": "form#profile",
                    "idempotency_key": "submit-profile-v1",
                }],
            )
        self.assertEqual(executor.actions, [])

    async def test_approved_mutation_executes_once_with_idempotency_key(self):
        executor = FakeExecutor()
        approvals = []

        async def approve(action, token):
            approvals.append((action.kind, action.idempotency_key, token))
            return token == "approved-token"

        AgentRunner.configure(
            executor=executor,
            approval_authorizer=approve,
            allowed_hosts=["example.com"],
            resolver=lambda host: ["93.184.216.34"],
        )
        result = await AgentRunner.run_claw_task(
            "Click the approved control",
            "test-model",
            actions=[{
                "kind": "click",
                "url": "https://example.com/settings",
                "selector": "button#save",
                "idempotency_key": "save-settings-42",
            }],
            approval_token="approved-token",
        )
        self.assertTrue(result["steps"][0]["mutating"])
        self.assertEqual(approvals, [("click", "save-settings-42", "approved-token")])
        self.assertEqual(len(executor.actions), 1)

    async def test_private_or_non_allowlisted_destination_is_rejected(self):
        executor = FakeExecutor()
        AgentRunner.configure(
            executor=executor,
            allowed_hosts=["internal.example.com"],
            resolver=lambda host: ["127.0.0.1"],
        )
        with self.assertRaisesRegex(BrowserPolicyError, "non-public"):
            await AgentRunner.run_claw_task(
                "Inspect internal host",
                "test-model",
                actions=[{"kind": "inspect", "url": "https://internal.example.com/admin"}],
            )

        AgentRunner.configure(
            executor=executor,
            allowed_hosts=["example.com"],
            resolver=lambda host: ["93.184.216.34"],
        )
        with self.assertRaisesRegex(BrowserPolicyError, "not allowlisted"):
            await AgentRunner.run_claw_task(
                "Inspect unexpected host",
                "test-model",
                actions=[{"kind": "inspect", "url": "https://evil.invalid/"}],
            )

    async def test_mutations_require_dedupe_and_upload_uses_artifact_id(self):
        executor = FakeExecutor()
        AgentRunner.configure(
            executor=executor,
            approval_authorizer=lambda action, token: True,
            allowed_hosts=["example.com"],
            resolver=lambda host: ["93.184.216.34"],
        )
        with self.assertRaisesRegex(BrowserPolicyError, "idempotency_key"):
            await AgentRunner.run_claw_task(
                "Click",
                "test-model",
                actions=[{"kind": "click", "url": "https://example.com", "selector": "button"}],
                approval_token="approved",
            )
        with self.assertRaisesRegex(BrowserPolicyError, "artifact_id"):
            await AgentRunner.run_claw_task(
                "Upload",
                "test-model",
                actions=[{
                    "kind": "upload",
                    "url": "https://example.com/upload",
                    "selector": "input[type=file]",
                    "idempotency_key": "upload-1",
                }],
                approval_token="approved",
            )


if __name__ == "__main__":
    unittest.main()
