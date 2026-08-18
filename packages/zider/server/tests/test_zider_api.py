import unittest
import base64
import sys
from pathlib import Path

ZIDER_ROOT = Path(__file__).resolve().parent.parent
if str(ZIDER_ROOT) not in sys.path:
    sys.path.insert(0, str(ZIDER_ROOT))

import warnings
warnings.filterwarnings("ignore", message=".*starlette.testclient.*")

from fastapi.testclient import TestClient
from app.main import app


class TestZiderAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "zider-bff")

    def test_write_endpoint(self):
        resp = self.client.post("/api/write", json={
            "action": "improve",
            "text": "Hello world this is test",
            "tone": "professional"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("result", data)
        self.assertEqual(data["action"], "improve")

    def test_translate_endpoint(self):
        resp = self.client.post("/api/translate", json={
            "text": "Hello world",
            "source_lang": "en",
            "target_lang": "es"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("translated_text", data)

    def test_batch_translate_endpoint(self):
        resp = self.client.post("/api/translate/batch", json={
            "items": ["Title text", "Paragraph description"],
            "source_lang": "en",
            "target_lang": "es"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["items"]), 2)

    def test_summarize_endpoint(self):
        resp = self.client.post("/api/summarize/webpage", json={
            "raw_text": "This is a detailed paragraph discussing modern browser extensions and AI sidebars."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("summary", data)

    def test_summarize_endpoint_rejects_ssrf_and_private_addresses(self):
        resp = self.client.post("/api/summarize/webpage", json={
            "url": "http://localhost:8080/internal-secrets"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("Could not fetch", data["summary"])

        resp2 = self.client.post("/api/summarize/webpage", json={
            "url": "http://127.0.0.1:9569/api/v1/overview"
        })
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertIn("Could not fetch", data2["summary"])

        resp3 = self.client.post("/api/summarize/webpage", json={
            "url": "file:///etc/passwd"
        })
        self.assertEqual(resp3.status_code, 200)
        data3 = resp3.json()
        self.assertIn("Could not fetch", data3["summary"])

    def test_search_endpoint(self):
        resp = self.client.post("/api/search", json={
            "query": "artificial intelligence latest trends",
            "max_results": 3
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("results", data)
        self.assertTrue(len(data["results"]) > 0)

    def test_prompts_endpoint(self):
        resp = self.client.get("/api/prompts")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(len(data) > 0)
        self.assertIn("template", data[0])

    def test_vision_analyze_endpoint(self):
        sample_b64 = base64.b64encode(b"fake_image_bytes").decode("utf-8")
        resp = self.client.post("/api/vision/analyze", json={
            "image_base64": f"data:image/png;base64,{sample_b64}",
            "prompt": "Extract text"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("analysis", data)

    def test_image_generate_endpoint(self):
        resp = self.client.post("/api/image/generate", json={
            "prompt": "Cyberpunk workspace with neon blue lights",
            "style": "photorealistic"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("image_url", data)

    def test_zworkforce_bridge_endpoints(self):
        resp = self.client.get("/api/zworkforce/overview")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)

        dispatch_resp = self.client.post("/api/zworkforce/dispatch", json={
            "title": "Analyze Data Task",
            "prompt": "Extract structured dataset",
            "target_agent": "general"
        })
        self.assertEqual(dispatch_resp.status_code, 200)
        dispatch_data = dispatch_resp.json()
        self.assertIn("task_id", dispatch_data)

    def test_agent_run_requires_explicit_structured_actions(self):
        resp = self.client.post("/api/agent/run", json={
            "goal": "Extract table headers from current view"
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("explicit structured actions", resp.json()["detail"])

    def test_agent_run_fails_closed_when_executor_is_unconfigured(self):
        resp = self.client.post("/api/agent/run", json={
            "goal": "Inspect the approved page",
            "actions": [{
                "kind": "inspect",
                "url": "https://example.com/"
            }]
        })
        self.assertEqual(resp.status_code, 503)
        self.assertIn("executor is not configured", resp.json()["detail"])


if __name__ == "__main__":
    unittest.main()
