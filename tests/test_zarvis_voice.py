import io
import json
import urllib.error
import unittest

from zworkforce.zarvis_voice import ZarvisVoiceConfig, ZarvisVoiceError, ZarvisVoiceService


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size=-1):
        return self.payload if size < 0 else self.payload[:size]


class ZarvisVoiceTests(unittest.TestCase):
    def config(self, **overrides):
        values = {
            "enabled": True,
            "gateway_url": "http://voice-gateway:8450",
            "service_token": "server-secret-token",
            "websocket_allowlist": ("wss://voice.example.com",),
            "model": "voice-local",
            "timeout_seconds": 2.0,
        }
        values.update(overrides)
        return ZarvisVoiceConfig(**values)

    def test_snapshot_never_serializes_service_token_or_gateway_url(self):
        service = ZarvisVoiceService(self.config())
        snapshot = service.snapshot()
        rendered = json.dumps(snapshot)
        self.assertNotIn("server-secret-token", rendered)
        self.assertNotIn("voice-gateway:8450", rendered)
        self.assertTrue(snapshot["enabled"])
        self.assertEqual(snapshot["websocket_origins"], ["wss://voice.example.com"])

    def test_issue_session_forwards_server_identity_and_returns_browser_safe_material(self):
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse({
                "ticket": "signed-ticket",
                "expires_at": "2026-08-15T00:01:00.000Z",
                "websocket_url": "wss://voice.example.com/v1/realtime",
                "ticket_transport": "sec-websocket-protocol",
            })

        service = ZarvisVoiceService(self.config(), opener=opener)
        result = service.issue_session(
            tenant_id="default",
            subject_id="bootstrap-test:operator",
            request_id="request-1",
        )
        self.assertEqual(captured["url"], "http://voice-gateway:8450/v1/voice/tickets")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer server-secret-token")
        self.assertEqual(captured["headers"]["X-tenant-id"], "default")
        self.assertEqual(captured["headers"]["X-subject-id"], "bootstrap-test:operator")
        self.assertEqual(captured["body"], {"model": "voice-local"})
        self.assertEqual(result["ticket"], "signed-ticket")
        self.assertEqual(result["websocket_url"], "wss://voice.example.com/v1/realtime")
        self.assertNotIn("service_token", result)
        self.assertNotIn("gateway_url", result)

    def test_denies_websocket_origin_not_in_allowlist(self):
        service = ZarvisVoiceService(
            self.config(),
            opener=lambda *_args, **_kwargs: FakeResponse({
                "ticket": "signed-ticket",
                "expires_at": "2026-08-15T00:01:00.000Z",
                "websocket_url": "wss://attacker.example/v1/realtime",
            }),
        )
        with self.assertRaises(ZarvisVoiceError) as ctx:
            service.issue_session(tenant_id="default", subject_id="user", request_id="request-2")
        self.assertEqual(ctx.exception.code, "voice_websocket_origin_denied")

    def test_disabled_service_fails_closed(self):
        service = ZarvisVoiceService(self.config(enabled=False))
        with self.assertRaises(ZarvisVoiceError) as ctx:
            service.issue_session(tenant_id="default", subject_id="user", request_id="request-3")
        self.assertEqual(ctx.exception.status, 503)
        self.assertEqual(ctx.exception.code, "voice_disabled")

    def test_upstream_http_error_does_not_reflect_upstream_body(self):
        def opener(request, timeout):
            raise urllib.error.HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                hdrs=None,
                fp=io.BytesIO(b'{"error":{"message":"secret details"}}'),
            )

        service = ZarvisVoiceService(self.config(), opener=opener)
        with self.assertRaises(ZarvisVoiceError) as ctx:
            service.issue_session(tenant_id="default", subject_id="user", request_id="request-4")
        self.assertEqual(ctx.exception.code, "voice_gateway_rejected")
        self.assertNotIn("secret details", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
