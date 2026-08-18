import asyncio
import unittest

from app.services.agent_runner import BrowserAction, BrowserPolicyError
from app.services.playwright_runtime import _execute_approved_mutation


class _Locator:
    def __init__(self):
        self.files = None
        self.first = self

    async def set_input_files(self, files, timeout):
        self.files = files


class _Page:
    def __init__(self):
        self.locator_obj = _Locator()

    def locator(self, selector):
        self.selector = selector
        return self.locator_obj


class PlaywrightUploadTests(unittest.TestCase):
    def test_upload_uses_governed_bytes_not_host_path(self):
        page = _Page()

        async def loader(artifact_id):
            self.assertEqual(artifact_id, "11111111-1111-1111-1111-111111111111")
            return {"name": "safe.txt", "mime_type": "text/plain", "buffer": b"hello", "sha256": "a" * 64}

        action = BrowserAction(
            kind="upload",
            url="https://example.com/form",
            selector="#file",
            artifact_id="11111111-1111-1111-1111-111111111111",
            idempotency_key="upload-1",
        )
        result = asyncio.run(_execute_approved_mutation(page, action, 1000, loader))
        self.assertEqual(page.selector, "#file")
        self.assertEqual(page.locator_obj.files["buffer"], b"hello")
        self.assertEqual(result["artifact_sha256"], "a" * 64)
        self.assertNotIn("path", page.locator_obj.files)

    def test_upload_without_governed_loader_fails_closed(self):
        page = _Page()
        action = BrowserAction(
            kind="upload",
            url="https://example.com/form",
            selector="#file",
            artifact_id="11111111-1111-1111-1111-111111111111",
            idempotency_key="upload-2",
        )
        with self.assertRaises(BrowserPolicyError):
            asyncio.run(_execute_approved_mutation(page, action, 1000, None))


if __name__ == "__main__":
    unittest.main()
