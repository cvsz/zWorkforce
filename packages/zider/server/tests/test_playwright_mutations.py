import sys
import unittest
from pathlib import Path

ZIDER_ROOT = Path(__file__).resolve().parent.parent
if str(ZIDER_ROOT) not in sys.path:
    sys.path.insert(0, str(ZIDER_ROOT))

from app.services.agent_runner import BrowserAction, BrowserPolicyError
from app.services.playwright_runtime import _execute_approved_mutation


class FakeLocator:
    def __init__(self):
        self.first = self
        self.clicks = []
        self.scripts = []

    async def click(self, *, timeout):
        self.clicks.append(timeout)

    async def evaluate(self, script):
        self.scripts.append(script)


class FakePage:
    def __init__(self):
        self.selectors = []
        self.target = FakeLocator()

    def locator(self, selector):
        self.selectors.append(selector)
        return self.target


class ApprovedMutationExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_click_executes_exact_approved_selector(self):
        page = FakePage()
        action = BrowserAction(
            kind="click",
            url="https://example.com/settings",
            selector="button#save",
            idempotency_key="save-1",
            resolved_addresses=("93.184.216.34",),
        )

        result = await _execute_approved_mutation(page, action, 5000)

        self.assertEqual(result, {"ok": True, "action": "click"})
        self.assertEqual(page.selectors, ["button#save"])
        self.assertEqual(page.target.clicks, [5000])

    async def test_submit_uses_form_request_submit_without_injecting_values(self):
        page = FakePage()
        action = BrowserAction(
            kind="submit",
            url="https://example.com/profile",
            selector="form#profile",
            value="sensitive-value-bound-by-approval-but-not-interpreted-here",
            idempotency_key="submit-1",
            resolved_addresses=("93.184.216.34",),
        )

        result = await _execute_approved_mutation(page, action, 5000)

        self.assertEqual(result, {"ok": True, "action": "submit"})
        self.assertEqual(page.selectors, ["form#profile"])
        self.assertEqual(len(page.target.scripts), 1)
        self.assertIn("requestSubmit", page.target.scripts[0])
        self.assertNotIn(action.value, page.target.scripts[0])

    async def test_upload_remains_fail_closed_without_artifact_content_adapter(self):
        page = FakePage()
        action = BrowserAction(
            kind="upload",
            url="https://example.com/upload",
            selector="input[type=file]",
            artifact_id="artifact-123",
            idempotency_key="upload-1",
            resolved_addresses=("93.184.216.34",),
        )

        with self.assertRaisesRegex(BrowserPolicyError, "artifact-content adapter"):
            await _execute_approved_mutation(page, action, 5000)


if __name__ == "__main__":
    unittest.main()
