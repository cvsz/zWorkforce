import sys
import unittest
from pathlib import Path

ZIDER_SERVER = Path(__file__).resolve().parent.parent / "packages" / "zider" / "server"
if str(ZIDER_SERVER) not in sys.path:
    sys.path.insert(0, str(ZIDER_SERVER))

from app.services.agent_runner import (
    AgentRunner,
    BrowserApprovalRequired,
    BrowserAutomationUnavailable,
    BrowserPolicyError,
)


class FakeExecutor:
    def __init__(self):
        self.actions = []

    async def execute(self, action):
        self.actions.append(action)
        return {"ok": True}


class ZiderBrowserContractRequiredCiTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        AgentRunner.reset()

    async def test_production_default_fails_closed_without_executor(self):
        AgentRunner.configure(allowed_hosts=["example.com"], resolver=lambda host: ["93.184.216.34"])
        with self.assertRaises(BrowserAutomationUnavailable):
            await AgentRunner.run_claw_task(
                "inspect",
                "test",
                actions=[{"kind": "inspect", "url": "https://example.com/"}],
            )

    async def test_private_destination_and_unapproved_mutation_are_denied(self):
        executor = FakeExecutor()
        AgentRunner.configure(
            executor=executor,
            allowed_hosts=["example.com"],
            resolver=lambda host: ["127.0.0.1"],
        )
        with self.assertRaises(BrowserPolicyError):
            await AgentRunner.run_claw_task(
                "inspect",
                "test",
                actions=[{"kind": "inspect", "url": "https://example.com/"}],
            )

        AgentRunner.configure(
            executor=executor,
            allowed_hosts=["example.com"],
            resolver=lambda host: ["93.184.216.34"],
        )
        with self.assertRaises(BrowserApprovalRequired):
            await AgentRunner.run_claw_task(
                "save",
                "test",
                actions=[{
                    "kind": "click",
                    "url": "https://example.com/settings?token=secret",
                    "selector": "button#save",
                    "idempotency_key": "save-1",
                }],
            )
        self.assertEqual(executor.actions, [])

    async def test_approved_action_runs_and_redacts_url_query_metadata(self):
        executor = FakeExecutor()
        AgentRunner.configure(
            executor=executor,
            approval_authorizer=lambda action, token: token == "approved",
            allowed_hosts=["example.com"],
            resolver=lambda host: ["93.184.216.34"],
        )
        result = await AgentRunner.run_claw_task(
            "save",
            "test",
            actions=[{
                "kind": "submit",
                "url": "https://example.com/form?token=secret#private",
                "selector": "form#settings",
                "idempotency_key": "submit-1",
            }],
            approval_token="approved",
        )
        self.assertEqual(result["steps"][0]["url"], "https://example.com/form")
        self.assertTrue(result["steps"][0]["mutating"])
        self.assertEqual(len(executor.actions), 1)


if __name__ == "__main__":
    unittest.main()
