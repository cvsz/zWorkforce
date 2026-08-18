import sys
import unittest
from pathlib import Path

ZIDER_ROOT = Path(__file__).resolve().parent.parent
if str(ZIDER_ROOT) not in sys.path:
    sys.path.insert(0, str(ZIDER_ROOT))

from app.services.agent_runner import AgentRunner


class CapturingExecutor:
    enforces_resolved_addresses = True
    def __init__(self):
        self.actions = []
    async def execute(self, action):
        self.actions.append(action)
        return {"ok": True}


class AgentRunnerEffectBindingTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        AgentRunner.reset()

    async def test_authorized_mutation_carries_exact_approval_task_id(self):
        executor = CapturingExecutor()
        async def approve(action, token):
            return token == "123e4567-e89b-12d3-a456-426614174000"
        AgentRunner.configure(
            executor=executor,
            approval_authorizer=approve,
            allowed_hosts=["example.com"],
            resolver=lambda host: ["93.184.216.34"],
        )
        await AgentRunner.run_claw_task(
            "save profile",
            "test",
            actions=[{
                "kind": "click",
                "url": "https://example.com/profile",
                "selector": "button#save",
                "idempotency_key": "effect-bind-1",
            }],
            approval_token="123e4567-e89b-12d3-a456-426614174000",
        )
        self.assertEqual(executor.actions[0].approval_task_id, "123e4567-e89b-12d3-a456-426614174000")


if __name__ == "__main__":
    unittest.main()
