import sys
import unittest
from pathlib import Path

ZIDER_ROOT = Path(__file__).resolve().parent.parent
if str(ZIDER_ROOT) not in sys.path:
    sys.path.insert(0, str(ZIDER_ROOT))

from app.services.agent_runner import BrowserAction
from app.services.browser_executor import PinnedBrowserExecutor


class FakeTransport:
    enforces_pinned_destination = True
    disables_automatic_redirects = True
    verifies_tls_server_identity = True

    def __init__(self):
        self.calls = []

    async def request(self, **kwargs):
        self.calls.append(kwargs)
        return {"ok": True}


class BrowserExecutorIPv6Tests(unittest.IsolatedAsyncioTestCase):
    async def test_executor_brackets_ipv6_host_authority(self):
        transport = FakeTransport()
        action = BrowserAction(
            kind="inspect",
            url="https://[2606:2800:220:1:248:1893:25c8:1946]/page",
            resolved_addresses=("2606:2800:220:1:248:1893:25c8:1946",),
        )
        await PinnedBrowserExecutor(transport).execute(action)
        self.assertEqual(
            transport.calls[0]["host_header"],
            "[2606:2800:220:1:248:1893:25c8:1946]",
        )
        self.assertEqual(
            transport.calls[0]["tls_server_name"],
            "2606:2800:220:1:248:1893:25c8:1946",
        )


if __name__ == "__main__":
    unittest.main()
