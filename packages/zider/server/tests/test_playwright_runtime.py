import base64
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ZIDER_ROOT = Path(__file__).resolve().parent.parent
if str(ZIDER_ROOT) not in sys.path:
    sys.path.insert(0, str(ZIDER_ROOT))

from app.services.agent_runner import BrowserAction, BrowserAutomationUnavailable, BrowserPolicyError
from app.services.browser_runtime import configure_browser_runtime
from app.services.playwright_runtime import MAX_SCREENSHOT_BYTES, PlaywrightReadOnlyTransport, _encode_screenshot


class PlaywrightRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_runtime_is_safe_default(self):
        with patch.dict(os.environ, {"ZIDER_BROWSER_RUNTIME": "disabled"}, clear=False):
            self.assertEqual(await configure_browser_runtime(), "disabled")

    async def test_unknown_runtime_fails_closed(self):
        with patch.dict(os.environ, {"ZIDER_BROWSER_RUNTIME": "unexpected"}, clear=False):
            with self.assertRaisesRegex(BrowserAutomationUnavailable, "unsupported"):
                await configure_browser_runtime()

    async def test_transport_rejects_mutation_before_loading_browser(self):
        transport = PlaywrightReadOnlyTransport()
        action = BrowserAction(
            kind="click",
            url="https://example.com/settings",
            selector="button#save",
            idempotency_key="save-1",
            resolved_addresses=("93.184.216.34",),
        )
        with self.assertRaisesRegex(BrowserPolicyError, "approval adapter"):
            await transport.request(
                action=action,
                connect_ip="93.184.216.34",
                host_header="example.com",
                tls_server_name="example.com",
                timeout_seconds=5,
            )

    async def test_transport_rejects_tls_identity_mismatch_before_loading_browser(self):
        transport = PlaywrightReadOnlyTransport()
        action = BrowserAction(
            kind="inspect",
            url="https://example.com/page",
            resolved_addresses=("93.184.216.34",),
        )
        with self.assertRaisesRegex(BrowserPolicyError, "TLS server identity"):
            await transport.request(
                action=action,
                connect_ip="93.184.216.34",
                host_header="example.com",
                tls_server_name="other.example.com",
                timeout_seconds=5,
            )

    async def test_transport_rejects_host_authority_mismatch_before_loading_browser(self):
        transport = PlaywrightReadOnlyTransport()
        action = BrowserAction(
            kind="inspect",
            url="https://example.com:8443/page",
            resolved_addresses=("93.184.216.34",),
        )
        with self.assertRaisesRegex(BrowserPolicyError, "Host authority"):
            await transport.request(
                action=action,
                connect_ip="93.184.216.34",
                host_header="example.com",
                tls_server_name="example.com",
                timeout_seconds=5,
            )

    async def test_screenshot_encoding_is_real_png_payload_and_bounded(self):
        raw = b"\x89PNG\r\n\x1a\nexample"
        payload = _encode_screenshot(raw)
        self.assertEqual(payload["mime_type"], "image/png")
        self.assertEqual(payload["bytes"], len(raw))
        self.assertEqual(base64.b64decode(payload["image_base64"]), raw)
        with self.assertRaisesRegex(BrowserAutomationUnavailable, "empty"):
            _encode_screenshot(b"")
        with self.assertRaisesRegex(BrowserAutomationUnavailable, "response bound"):
            _encode_screenshot(b"x" * (MAX_SCREENSHOT_BYTES + 1))


if __name__ == "__main__":
    unittest.main()
