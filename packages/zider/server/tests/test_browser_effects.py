import asyncio
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
    def __init__(self, result=None, error=None, block=False):
        self.result = result if result is not None else {"ok": True}
        self.error = error
        self.block = block
        self.calls = 0
    async def execute(self, action):
        self.calls += 1
        if self.block:
            await asyncio.Event().wait()
        if self.error:
            raise self.error
        return self.result


class FakeController:
    def __init__(self, status="not_started", claimed=True, cancel_claim=False, cancel_success_finish=False):
        self.status = status
        self.claimed = claimed
        self.cancel_claim = cancel_claim
        self.cancel_success_finish = cancel_success_finish
        self.finished = []
    async def begin(self, action, approval_task_id):
        return {"id": "123e4567-e89b-12d3-a456-426614174001", "status": self.status, "result_sha256": "a" * 64}
    async def claim(self, effect_id):
        if self.cancel_claim:
            raise asyncio.CancelledError()
        return ({"id": effect_id, "status": "executing" if self.claimed else "not_started"}, self.claimed)
    async def finish(self, effect_id, *, status, result_sha256="", error_code=""):
        if status == "succeeded" and self.cancel_success_finish:
            self.cancel_success_finish = False
            raise asyncio.CancelledError()
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

    async def test_outer_timeout_marks_claimed_execution_unknown(self):
        controller = FakeController()
        executor = DurableBrowserEffectExecutor(FakeDelegate(block=True), controller)
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(executor.execute(mutation()), timeout=0.01)
        self.assertEqual(controller.finished[-1], ("unknown", "", "execution_canceled"))

    async def test_cancellation_during_claim_never_executes_and_cancels_claimed_effect(self):
        delegate = FakeDelegate()
        controller = FakeController(cancel_claim=True)
        with self.assertRaises(asyncio.CancelledError):
            await DurableBrowserEffectExecutor(delegate, controller).execute(mutation())
        self.assertEqual(delegate.calls, 0)
        self.assertEqual(controller.finished[-1], ("canceled", "", "claim_canceled"))

    async def test_cancellation_while_recording_success_quarantines_unknown(self):
        controller = FakeController(cancel_success_finish=True)
        with self.assertRaises(asyncio.CancelledError):
            await DurableBrowserEffectExecutor(FakeDelegate(), controller).execute(mutation())
        self.assertEqual(controller.finished[-1], ("unknown", "", "completion_canceled"))

    async def test_missing_approval_binding_fails_closed(self):
        delegate = FakeDelegate()
        with self.assertRaises(BrowserAutomationUnavailable):
            await DurableBrowserEffectExecutor(delegate, FakeController()).execute(mutation(approval_task_id=""))
        self.assertEqual(delegate.calls, 0)

    async def test_cancel_during_execution_marks_unknown_and_fails_closed(self):
        delegate = FakeDelegate()
        controller = FakeController()

        async def canceled(action):
            return True

        with self.assertRaisesRegex(BrowserAutomationUnavailable, "canceled during execution"):
            await DurableBrowserEffectExecutor(delegate, controller, cancel_checker=canceled).execute(mutation())
        self.assertEqual(delegate.calls, 1)
        self.assertEqual(controller.finished[-1][0], "unknown")
        self.assertEqual(controller.finished[-1][2], "canceled_during_execution")

    async def test_cancel_checker_false_finishes_succeeded(self):
        controller = FakeController()

        async def not_canceled(action):
            return False

        result = await DurableBrowserEffectExecutor(
            FakeDelegate(), controller, cancel_checker=not_canceled
        ).execute(mutation())
        self.assertEqual(controller.finished[-1][0], "succeeded")
        self.assertEqual(result["effect_id"], "123e4567-e89b-12d3-a456-426614174001")

    async def test_cancel_checker_failure_does_not_block_success(self):
        controller = FakeController()

        async def broken(action):
            raise OSError("control plane unreachable")

        result = await DurableBrowserEffectExecutor(
            FakeDelegate(), controller, cancel_checker=broken
        ).execute(mutation())
        self.assertEqual(controller.finished[-1][0], "succeeded")
        self.assertTrue(result["ok"])

    async def test_cancel_never_replays_unknown_effect(self):
        delegate = FakeDelegate()

        async def canceled(action):
            return True

        with self.assertRaises(BrowserAutomationUnavailable):
            await DurableBrowserEffectExecutor(
                delegate, FakeController(status="unknown"), cancel_checker=canceled
            ).execute(mutation())
        self.assertEqual(delegate.calls, 0)


if __name__ == "__main__":
    unittest.main()
