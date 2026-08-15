"""
Unit tests for Z.A.R.V.I.S. speech provider registry, STT/TTS protocols,
and fake providers.
"""
import sys
import os
import unittest

# Allow running from the speech directory or from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from speech.registry import SpeechProviderRegistry, DuplicateProviderError, ProviderNotFoundError
from speech.providers.fake import FakeSTTProvider, FakeTTSProvider


class TestRegistrySTT(unittest.TestCase):
    def _make(self):
        return SpeechProviderRegistry()

    def test_register_and_get(self):
        reg = self._make()
        prov = FakeSTTProvider()
        reg.register_stt("fake", prov)
        self.assertIs(reg.get_stt("fake"), prov)

    def test_duplicate_raises(self):
        reg = self._make()
        reg.register_stt("fake", FakeSTTProvider())
        with self.assertRaises(DuplicateProviderError):
            reg.register_stt("fake", FakeSTTProvider())

    def test_missing_raises(self):
        reg = self._make()
        with self.assertRaises(ProviderNotFoundError):
            reg.get_stt("nonexistent")

    def test_empty_name_raises(self):
        reg = self._make()
        with self.assertRaises(ValueError):
            reg.register_stt("", FakeSTTProvider())

    def test_list_stt_sorted(self):
        reg = self._make()
        reg.register_stt("z", FakeSTTProvider())
        reg.register_stt("a", FakeSTTProvider())
        self.assertEqual(reg.list_stt(), ["a", "z"])


class TestRegistryTTS(unittest.TestCase):
    def _make(self):
        return SpeechProviderRegistry()

    def test_register_and_get(self):
        reg = self._make()
        prov = FakeTTSProvider()
        reg.register_tts("fake", prov)
        self.assertIs(reg.get_tts("fake"), prov)

    def test_duplicate_raises(self):
        reg = self._make()
        reg.register_tts("fake", FakeTTSProvider())
        with self.assertRaises(DuplicateProviderError):
            reg.register_tts("fake", FakeTTSProvider())

    def test_missing_raises(self):
        reg = self._make()
        with self.assertRaises(ProviderNotFoundError):
            reg.get_tts("nonexistent")

    def test_health_summary_no_credentials(self):
        reg = self._make()
        reg.register_stt("s1", FakeSTTProvider())
        reg.register_tts("t1", FakeTTSProvider())
        summary = reg.health_summary()
        self.assertIn("stt_providers", summary)
        self.assertIn("tts_providers", summary)
        self.assertNotIn("credentials", str(summary))
        self.assertNotIn("token", str(summary))
        self.assertNotIn("secret", str(summary))


class TestFakeSTT(unittest.TestCase):
    def test_transcribe_returns_text(self):
        prov = FakeSTTProvider(text="hello world")
        result = prov.transcribe(b"\x00" * 32000)
        self.assertEqual(result.text, "hello world")
        self.assertEqual(result.provider, "fake")
        self.assertTrue(result.is_final)

    def test_transcribe_raises_on_error(self):
        prov = FakeSTTProvider(raise_on_transcribe=RuntimeError("backend down"))
        with self.assertRaises(RuntimeError):
            prov.transcribe(b"\x00" * 100)

    def test_health_reports_healthy(self):
        status = FakeSTTProvider(healthy=True).health()
        self.assertTrue(status.healthy)
        self.assertIsNone(status.error)

    def test_health_reports_unhealthy(self):
        status = FakeSTTProvider(healthy=False).health()
        self.assertFalse(status.healthy)
        self.assertIsNotNone(status.error)

    def test_capability_locality_is_local(self):
        prov = FakeSTTProvider()
        self.assertEqual(prov.capability.locality, "local")


class TestFakeTTS(unittest.TestCase):
    def test_synthesize_returns_audio(self):
        prov = FakeTTSProvider(audio_bytes=b"\x01" * 32000)
        result = prov.synthesize("hello")
        self.assertEqual(result.audio_bytes, b"\x01" * 32000)
        self.assertEqual(result.provider, "fake")

    def test_synthesize_raises_on_error(self):
        prov = FakeTTSProvider(raise_on_synthesize=RuntimeError("backend down"))
        with self.assertRaises(RuntimeError):
            prov.synthesize("test")

    def test_health_reports_healthy(self):
        status = FakeTTSProvider(healthy=True).health()
        self.assertTrue(status.healthy)

    def test_health_reports_unhealthy(self):
        status = FakeTTSProvider(healthy=False).health()
        self.assertFalse(status.healthy)

    def test_capability_no_credentials(self):
        cap = FakeTTSProvider().capability
        cap_str = str(cap)
        self.assertNotIn("token", cap_str)
        self.assertNotIn("secret", cap_str)
        self.assertNotIn("key", cap_str.lower())


if __name__ == "__main__":
    unittest.main()
