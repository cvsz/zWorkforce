import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from tests.common import stack
from zworkforce.api import App
from zworkforce.acp import ACP_PROTOCOL_VERSION


class ACPProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()
        self.app = App(self.settings, self.db, self.engine, self.auth, self.provider)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.app.handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.engine.shutdown()
        self.temp.cleanup()

    def acp_post(self, body, token="test-admin-secret"):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.base + "/acp", data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read()), resp.headers.get("ACP-Protocol-Version")

    def test_initialize(self):
        status, data, version = self.acp_post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertEqual(status, 200)
        self.assertEqual(version, ACP_PROTOCOL_VERSION)
        self.assertEqual(data["result"]["protocolVersion"], ACP_PROTOCOL_VERSION)
        self.assertEqual(data["result"]["agentInfo"]["name"], "zWorkforce-Agent")

    def test_authenticate(self):
        status, data, _ = self.acp_post({"jsonrpc": "2.0", "id": 2, "method": "authenticate", "params": {}})
        self.assertEqual(status, 200)
        self.assertTrue(data["result"]["authenticated"])
        self.assertEqual(data["result"]["tenantId"], "default")

    def test_new_and_load_session(self):
        # Create session
        _, new_data, _ = self.acp_post({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "newSession",
            "params": {"agentId": "researcher", "initialPrompt": "Research AI topics"}
        })
        session_id = new_data["result"]["sessionId"]
        self.assertIsNotNone(session_id)

        # Load session
        status, load_data, _ = self.acp_post({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "loadSession",
            "params": {"sessionId": session_id}
        })
        self.assertEqual(status, 200)
        self.assertEqual(load_data["result"]["session"]["id"], session_id)

    def test_prompt_dispatch(self):
        status, data, _ = self.acp_post({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "prompt",
            "params": {"agentId": "researcher", "content": "Please analyze system status"}
        })
        self.assertEqual(status, 200)
        self.assertIn("taskId", data["result"])
        self.assertEqual(data["result"]["status"], "queued")


if __name__ == "__main__":
    unittest.main()
