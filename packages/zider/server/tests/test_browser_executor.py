import sys
import unittest
from pathlib import Path

ZIDER_ROOT = Path(__file__).resolve().parent.parent
if str(ZIDER_ROOT) not in sys.path:
    sys.path.insert(0, str(ZIDER_ROOT))

from app.services.agent_runner import BrowserAction, BrowserPolicyError
from app.services.browser_executor import PinnedBrowserExecutor


class FakeTransport:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or {"ok": True}

    async def request(self, **kwargs):
        self.calls.append(kwargs)
        return dict(self.result)


class BrowserExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def test_executor_uses_policy_pinned_address_and_original_host(self):
        transport = FakeTransport()
        executor = PinnedBrowserExecutor(transport)
        action = BrowserAction(
            kind="inspect",
            url="https://docs.example.com/page",
            resolved_addresses=("93.184.216.34",),
        )
        result = await executor.execute(action)
        self.assertTrue(result["ok"])
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(transport.calls[0]["connect_ip"], "93.184.216.34")
        self.assertEqual(transport.calls[0]["host_header"], "docs.example.com")

    async def test_executor_rejects_private_or_missing_pins(self):
        executor = PinnedBrowserExecutor(FakeTransport())
        with self.assertRaisesRegex(BrowserPolicyError, "must be public"):
            await executor.execute(BrowserAction(kind="inspect", url="https://example.com", resolved_addresses=("127.0.0.1",)))
        with self.assertRaisesRegex(BrowserPolicyError, "requires policy-validated"):
            await executor.execute(BrowserAction(kind="inspect", url="https://example.com"))

    async def test_executor_never_follows_redirect_without_revalidation(self):
        transport = FakeTransport({"redirect_url": "https://other.example.com/next"})
        executor = PinnedBrowserExecutor(transport)
        action = BrowserAction(
            kind="navigate",
            url="https://example.com/start",
            resolved_addresses=("93.184.216.34",),
        )
        with self.assertRaisesRegex(BrowserPolicyError, "redirects require policy revalidation"):
            await executor.execute(action)


if __name__ == "__main__":
    unittest.main()
