"""
STT (Speech-to-Text) protocol and result model for Z.A.R.V.I.S. voice-agent.

All STT providers must implement STTProvider. No provider credentials or
personal data are returned in HealthStatus; raw audio is never logged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class STTCapability:
    """Static capability declaration for an STT provider."""
    name: str
    locality: str  # "local" | "cloud"
    languages: tuple[str, ...] = ("en",)
    streaming: bool = False
    vad_integrated: bool = False
    timeout_seconds: float = 10.0
    max_audio_seconds: float = 300.0


@dataclass(frozen=True)
class STTResult:
    """Result of a single STT transcription request."""
    text: str
    language: str
    confidence: float  # 0.0 – 1.0; -1.0 when not reported
    duration_seconds: float
    provider: str
    model: str
    is_final: bool = True
    segments: tuple = field(default_factory=tuple)


@dataclass(frozen=True)
class STTHealthStatus:
    """Health report for an STT provider (must never include credentials)."""
    provider: str
    locality: str
    healthy: bool
    latency_ms: float | None = None
    error: str | None = None


@runtime_checkable
class STTProvider(Protocol):
    """Protocol all STT providers must satisfy."""

    @property
    def capability(self) -> STTCapability:
        """Static capability declaration."""
        ...

    def transcribe(self, audio_bytes: bytes, *, language: str = "en") -> STTResult:
        """
        Transcribe PCM-16 audio bytes to text.

        Raises RuntimeError on provider failure. Never logs audio bytes.
        """
        ...

    def health(self) -> STTHealthStatus:
        """
        Return provider health without exposing credentials or raw audio.
        """
        ...
