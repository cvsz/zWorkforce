import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ZIDER_ROOT = Path(__file__).resolve().parent.parent
if str(ZIDER_ROOT) not in sys.path:
    sys.path.insert(0, str(ZIDER_ROOT))

import app.services.browser_effects as effects_module
from app.services.agent_runner import BrowserAction
from app.services.browser_effects import ZWorkforceBrowserEffectController
from app.services.zworkforce_bridge import ZWorkforceBridge


class FakeResponse:
    status_code = 200
    def __init__(self, payload):
        self.payload = payload
    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.requests = []
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc, tb): return False
    async def post(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return self.response


class BrowserEffectControllerContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_begin_uses_authenticated_control_plane_and_action_digest(self):
        old_url, old_token = ZWorkforceBridge.ZWF_URL, ZWorkforceBridge.ZWF_TOKEN
        ZWorkforceBridge.ZWF_URL = "https://zwf.example.test"
        ZWorkforceBridge.ZWF_TOKEN = "server-secret"
        client = FakeClient(FakeResponse({"id": "123e4567-e89b-12d3-a456-426614174001", "status": "not_started"}))
        action = BrowserAction(kind="click", url="https://example.com", selector="button", idempotency_key="effect-1", approval_task_id="123e4567-e89b-12d3-a456-426614174000")
        try:
            with patch.object(effects_module.httpx, "AsyncClient", return_value=client):
                result = await ZWorkforceBrowserEffectController().begin(action, action.approval_task_id)
        finally:
            ZWorkforceBridge.ZWF_URL, ZWorkforceBridge.ZWF_TOKEN = old_url, old_token
        self.assertEqual(result["status"], "not_started")
        self.assertEqual(client.requests[0][0], "https://zwf.example.test/api/v1/browser-effects")
        self.assertEqual(client.requests[0][1]["headers"]["Authorization"], "Bearer server-secret")
        self.assertEqual(len(client.requests[0][1]["json"]["action_sha256"]), 64)


if __name__ == "__main__": unittest.main()
