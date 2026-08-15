"""
Fake STT and TTS providers for deterministic unit and integration tests.

These providers never make network calls or load model weights. They are
registered only in test environments and must not appear in production builds.
"""
from __future__ import annotations

import time
from ..stt import STTCapability, STTHealthStatus, STTResult
from ..tts import TTSCapability, TTSHealthStatus, TTSResult


class FakeSTTProvider:
    """Returns a configurable canned transcription without network calls."""

    def __init__(
        self,
        *,
        text: str = "test transcription",
        confidence: float = 0.99,
        healthy: bool = True,
        latency_ms: float = 5.0,
        raise_on_transcribe: Exception | None = None,
    ) -> None:
        self._text = text
        self._confidence = confidence
        self._healthy = healthy
        self._latency_ms = latency_ms
        self._raise = raise_on_transcribe
        self._capability = STTCapability(
            name="fake",
            locality="local",
            streaming=False,
            vad_integrated=False,
            timeout_seconds=1.0,
        )

    @property
    def capability(self) -> STTCapability:
        return self._capability

    def transcribe(self, audio_bytes: bytes, *, language: str = "en") -> STTResult:
        if self._raise is not None:
            raise self._raise  # noqa: raise-missing-from
        return STTResult(
            text=self._text,
            language=language,
            confidence=self._confidence,
            duration_seconds=len(audio_bytes) / (16000 * 2) if audio_bytes else 0.0,
            provider="fake",
            model="fake-1",
        )

    def health(self) -> STTHealthStatus:
        return STTHealthStatus(
            provider="fake",
            locality="local",
            healthy=self._healthy,
            latency_ms=self._latency_ms if self._healthy else None,
            error=None if self._healthy else "simulated failure",
        )


class FakeTTSProvider:
    """Returns a configurable canned PCM-16 payload without network calls."""

    def __init__(
        self,
        *,
        audio_bytes: bytes = b"\x00\x00" * 8000,  # 0.5 s silence
        healthy: bool = True,
        latency_ms: float = 5.0,
        raise_on_synthesize: Exception | None = None,
    ) -> None:
        self._audio = audio_bytes
        self._healthy = healthy
        self._latency_ms = latency_ms
        self._raise = raise_on_synthesize
        self._capability = TTSCapability(
            name="fake",
            locality="local",
            voices=("default",),
            formats=("pcm16",),
            sample_rates=(16000,),
            streaming=False,
            timeout_seconds=1.0,
        )

    @property
    def capability(self) -> TTSCapability:
        return self._capability

    def synthesize(
        self,
        text: str,
        *,
        voice: str = "default",
        format: str = "pcm16",
        sample_rate: int = 16000,
    ) -> TTSResult:
        if self._raise is not None:
            raise self._raise  # noqa: raise-missing-from
        return TTSResult(
            audio_bytes=self._audio,
            format=format,
            sample_rate=sample_rate,
            duration_seconds=len(self._audio) / (sample_rate * 2),
            provider="fake",
            model="fake-1",
            voice=voice,
        )

    def health(self) -> TTSHealthStatus:
        return TTSHealthStatus(
            provider="fake",
            locality="local",
            healthy=self._healthy,
            latency_ms=self._latency_ms if self._healthy else None,
            error=None if self._healthy else "simulated failure",
        )
