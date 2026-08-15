import io
import json
import unittest
from unittest.mock import patch

from zworkforce.zktcoder import (
    BANNER,
    KNOWN_FREE_MODELS,
    ZktCoderError,
    chat,
    list_models,
    main,
    run,
)


class ZktCoderChatTests(unittest.TestCase):
    def test_chat_returns_assistant_text(self):
        payload = json.dumps(
            {"choices": [{"message": {"role": "assistant", "content": "Done."}}]}
        ).encode("utf-8")

        def fake_urlopen(req, timeout=None):
            self.assertIn("/chat/completions", req.full_url)
            self.assertEqual(req.get_header("Authorization"), "Bearer test-key")
            return io.BytesIO(payload)

        with patch("zworkforce.zktcoder.urllib.request.urlopen", side_effect=fake_urlopen):
            out = chat("Write code", base_url="http://gw:9569/v1", api_key="test-key", model="deepseek/deepseek-v4-flash")

        self.assertEqual(out, "Done.")

    def test_chat_handles_list_content(self):
        payload = json.dumps(
            {"choices": [{"message": {"role": "assistant", "content": [{"type": "text", "text": "A"}, {"type": "text", "text": "B"}]}}]}
        ).encode("utf-8")

        def fake_urlopen(req, timeout=None):
            return io.BytesIO(payload)

        with patch("zworkforce.zktcoder.urllib.request.urlopen", side_effect=fake_urlopen):
            out = chat("Hi", base_url="http://gw:9569/v1")

        self.assertEqual(out, "A\nB")

    def test_chat_raises_on_http_error(self):
        import urllib.error

        class FakeHTTPError(urllib.error.HTTPError):
            def __init__(self):
                super().__init__("http://gw:9569/v1", 500, "boom", None, None)

            def read(self, amt=None):
                return b"internal error"

        with patch(
            "zworkforce.zktcoder.urllib.request.urlopen",
            side_effect=FakeHTTPError(),
        ):
            with self.assertRaises(ZktCoderError) as ctx:
                chat("Hi", base_url="http://gw:9569/v1")
            self.assertIn("500", str(ctx.exception))

    def test_chat_raises_on_no_choices(self):
        payload = json.dumps({"choices": []}).encode("utf-8")

        with patch("zworkforce.zktcoder.urllib.request.urlopen", return_value=io.BytesIO(payload)):
            with self.assertRaises(ZktCoderError):
                chat("Hi", base_url="http://gw:9569/v1")


class ZktCoderListModelsTests(unittest.TestCase):
    def test_list_models_returns_gateway_catalog(self):
        payload = json.dumps(
            {"data": [{"id": "anthropic/claude-fable-5"}, {"id": "deepseek/deepseek-v4-pro"}]}
        ).encode("utf-8")

        def fake_urlopen(req, timeout=None):
            self.assertIn("/models", req.full_url)
            return io.BytesIO(payload)

        with patch("zworkforce.zktcoder.urllib.request.urlopen", side_effect=fake_urlopen):
            models = list_models("http://gw:9569/v1", api_key="k")

        self.assertEqual(models, ["anthropic/claude-fable-5", "deepseek/deepseek-v4-pro"])

    def test_list_models_falls_back_when_gateway_unreachable(self):
        import urllib.error

        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError("down")

        with patch("zworkforce.zktcoder.urllib.request.urlopen", side_effect=fake_urlopen):
            models = list_models("http://gw:9569/v1")

        self.assertEqual(models, KNOWN_FREE_MODELS)


class ZktCoderCliTests(unittest.TestCase):
    def test_banner_contains_zktcoder(self):
        self.assertIn("ZKTCODER", BANNER)

    def test_run_rejects_empty_prompt(self):
        with patch("sys.stderr", new_callable=io.StringIO) as err:
            code = run("   ", quiet=True)
        self.assertEqual(code, 2)
        self.assertIn("no prompt", err.getvalue())

    def test_run_success_writes_output(self):
        with patch("zworkforce.zktcoder.chat", return_value="Refactored."), patch(
            "sys.stdout", new_callable=io.StringIO
        ) as out, patch("sys.stderr", new_callable=io.StringIO):
            code = run("Refactor math utils", base_url="http://gw:9569/v1", quiet=True)

        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), "Refactored.\n")

    def test_run_reports_gateway_failure(self):
        with patch(
            "zworkforce.zktcoder.chat", side_effect=ZktCoderError("gateway unreachable")
        ), patch("sys.stderr", new_callable=io.StringIO) as err, patch("sys.stdout", new_callable=io.StringIO):
            code = run("Hi", base_url="http://gw:9569/v1", quiet=True)

        self.assertEqual(code, 1)
        self.assertIn("gateway unreachable", err.getvalue())

    def test_main_list_models(self):
        with patch("zworkforce.zktcoder.list_models", return_value=["m1", "m2"]), patch(
            "sys.stdout", new_callable=io.StringIO
        ) as out, patch("sys.stderr", new_callable=io.StringIO):
            code = main(["--list-models", "--quiet"])

        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), "m1\nm2\n")

    def test_main_reads_stdin_prompt(self):
        with patch("zworkforce.zktcoder.run", return_value=0) as run_mock, patch(
            "sys.stdin", io.StringIO("Write tests")
        ):
            code = main(["--quiet"])

        self.assertEqual(code, 0)
        self.assertEqual(run_mock.call_args[0][0], "Write tests")


if __name__ == "__main__":
    unittest.main()
