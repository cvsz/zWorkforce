"""
TTS (Text-to-Speech) protocol and result model for Z.A.R.V.I.S. voice-agent.

All TTS providers must implement TTSProvider. No provider credentials are
returned in HealthStatus; synthesis output is audio bytes only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class TTSCapability:
    """Static capability declaration for a TTS provider."""
    name: str
    locality: str  # "local" | "cloud"
    voices: tuple[str, ...] = ()
    formats: tuple[str, ...] = ("pcm16",)
    sample_rates: tuple[int, ...] = (16000,)
    streaming: bool = False
    timeout_seconds: float = 10.0


@dataclass(frozen=True)
class TTSResult:
    """Result of a single TTS synthesis request."""
    audio_bytes: bytes
    format: str  # e.g. "pcm16", "mp3", "wav"
    sample_rate: int
    duration_seconds: float
    provider: str
    model: str
    voice: str


@dataclass(frozen=True)
class TTSHealthStatus:
    """Health report for a TTS provider (must never include credentials)."""
    provider: str
    locality: str
    healthy: bool
    latency_ms: float | None = None
    error: str | None = None


@runtime_checkable
class TTSProvider(Protocol):
    """Protocol all TTS providers must satisfy."""

    @property
    def capability(self) -> TTSCapability:
        """Static capability declaration."""
        ...

    def synthesize(
        self,
        text: str,
        *,
        voice: str = "default",
        format: str = "pcm16",
        sample_rate: int = 16000,
    ) -> TTSResult:
        """
        Synthesize text to audio bytes.

        Raises RuntimeError on provider failure.
        """
        ...

    def health(self) -> TTSHealthStatus:
        """
        Return provider health without exposing credentials.
        """
        ...
