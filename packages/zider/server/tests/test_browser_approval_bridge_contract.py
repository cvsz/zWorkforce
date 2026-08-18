import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ZIDER_ROOT = Path(__file__).resolve().parent.parent
if str(ZIDER_ROOT) not in sys.path:
    sys.path.insert(0, str(ZIDER_ROOT))

import app.services.zworkforce_bridge as bridge_module
from app.services.zworkforce_bridge import ZWorkforceBridge, ZWorkforceBridgeError


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload if payload is not None else {}

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return self.response


class BrowserApprovalBridgeContractTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.old_url = ZWorkforceBridge.ZWF_URL
        self.old_token = ZWorkforceBridge.ZWF_TOKEN
        ZWorkforceBridge.ZWF_URL = "https://zwf.example.test"
        ZWorkforceBridge.ZWF_TOKEN = "server-secret"

    def tearDown(self):
        ZWorkforceBridge.ZWF_URL = self.old_url
        ZWorkforceBridge.ZWF_TOKEN = self.old_token

    async def test_agent_lookup_is_server_authenticated_and_shape_checked(self):
        client = FakeClient(
            FakeResponse(
                payload={
                    "items": [
                        {
                            "id": "browser-review",
                            "enabled": True,
                            "requires_approval_for_mutations": True,
                            "required_approvals": 1,
                            "allowed_tools": [],
                            "skill_ids": [],
                        }
                    ]
                }
            )
        )
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=client):
            items = await ZWorkforceBridge.get_agents()
        self.assertEqual(items[0]["id"], "browser-review")
        self.assertEqual(client.requests[0][0], "https://zwf.example.test/api/v1/agents")
        self.assertEqual(client.requests[0][1]["headers"]["Authorization"], "Bearer server-secret")

        malformed = FakeClient(FakeResponse(payload={"items": "invalid"}))
        with patch.object(bridge_module.httpx, "AsyncClient", return_value=malformed):
            with self.assertRaisesRegex(ZWorkforceBridgeError, "response shape"):
                await ZWorkforceBridge.get_agents()


if __name__ == "__main__":
    unittest.main()
