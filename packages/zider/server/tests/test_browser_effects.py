import sys
import unittest
from pathlib import Path

ZIDER_ROOT = Path(__file__).resolve().parent.parent
if str(ZIDER_ROOT) not in sys.path:
    sys.path.insert(0, str(ZIDER_ROOT))

from app.services.agent_runner import BrowserAction, BrowserAutomationUnavailable
from app.services.browser_effects import DurableBrowserEffectExecutor


class FakeDelegate:
    enforces_resolved_addresses = True
    def __init__(self, result=None, error=None):
        self.result = result if result is not None else {"ok": True}
        self.error = error
        self.calls = 0
    async def execute(self, action):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


class FakeController:
    def __init__(self, status="not_started", claimed=True):
        self.status = status
        self.claimed = claimed
        self.finished = []
    async def begin(self, action, approval_task_id):
        return {"id": "123e4567-e89b-12d3-a456-426614174001", "status": self.status, "result_sha256": "a" * 64}
    async def claim(self, effect_id):
        return ({"id": effect_id, "status": "executing" if self.claimed else "not_started"}, self.claimed)
    async def finish(self, effect_id, *, status, result_sha256="", error_code=""):
        self.finished.append((status, result_sha256, error_code))
        return {"id": effect_id, "status": status}


def mutation(**overrides):
    values = {"kind": "click", "url": "https://example.com/profile", "selector": "button#save", "idempotency_key": "browser-effect-1", "resolved_addresses": ("93.184.216.34",), "approval_task_id": "123e4567-e89b-12d3-a456-426614174000"}
    values.update(overrides)
    return BrowserAction(**values)


class DurableBrowserEffectExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def test_claims_before_execution_and_finishes(self):
        delegate = FakeDelegate()
        controller = FakeController()
        result = await DurableBrowserEffectExecutor(delegate, controller).execute(mutation())
        self.assertEqual(delegate.calls, 1)
        self.assertEqual(controller.finished[-1][0], "succeeded")
        self.assertEqual(len(controller.finished[-1][1]), 64)
        self.assertTrue(result["effect_id"])

    async def test_succeeded_retry_deduplicates(self):
        delegate = FakeDelegate()
        result = await DurableBrowserEffectExecutor(delegate, FakeController(status="succeeded")).execute(mutation())
        self.assertEqual(delegate.calls, 0)
        self.assertTrue(result["deduplicated"])

    async def test_unknown_never_replays(self):
        delegate = FakeDelegate()
        with self.assertRaises(BrowserAutomationUnavailable):
            await DurableBrowserEffectExecutor(delegate, FakeController(status="unknown")).execute(mutation())
        self.assertEqual(delegate.calls, 0)

    async def test_execution_error_marks_unknown(self):
        controller = FakeController()
        with self.assertRaises(RuntimeError):
            await DurableBrowserEffectExecutor(FakeDelegate(error=RuntimeError("ambiguous")), controller).execute(mutation())
        self.assertEqual(controller.finished[-1][0], "unknown")

    async def test_missing_approval_binding_fails_closed(self):
        delegate = FakeDelegate()
        with self.assertRaises(BrowserAutomationUnavailable):
            await DurableBrowserEffectExecutor(delegate, FakeController()).execute(mutation(approval_task_id=""))
        self.assertEqual(delegate.calls, 0)


if __name__ == "__main__":
    unittest.main()
