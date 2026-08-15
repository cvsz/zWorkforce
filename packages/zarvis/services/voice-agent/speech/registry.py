"""
Speech provider registry for Z.A.R.V.I.S. voice-agent.

Each provider is registered exactly once by name. The registry is
build-time-immutable after the module is loaded. Providers are selected
explicitly by name; there is no silent fallback when a workload pins a
specific backend.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .stt import STTProvider
    from .tts import TTSProvider

log = logging.getLogger(__name__)


class DuplicateProviderError(RuntimeError):
    """Raised when a provider name is registered more than once."""


class ProviderNotFoundError(KeyError):
    """Raised when a requested provider name is not registered."""


class SpeechProviderRegistry:
    """Typed registry for STT and TTS provider instances.

    Usage::

        registry = SpeechProviderRegistry()
        registry.register_stt("whisper_local", whisper_provider)
        stt = registry.get_stt("whisper_local")
    """

    def __init__(self) -> None:
        self._stt: dict[str, "STTProvider"] = {}
        self._tts: dict[str, "TTSProvider"] = {}

    # --- STT ---

    def register_stt(self, name: str, provider: "STTProvider") -> None:
        """Register an STT provider. Raises DuplicateProviderError on collision."""
        if not name or not name.strip():
            raise ValueError("provider name must be a non-empty string")
        if name in self._stt:
            raise DuplicateProviderError(f"STT provider {name!r} is already registered")
        self._stt[name] = provider
        log.info("registered STT provider: %s (class=%s)", name, type(provider).__name__)

    def get_stt(self, name: str) -> "STTProvider":
        """Return the named STT provider. Raises ProviderNotFoundError if missing."""
        try:
            return self._stt[name]
        except KeyError as exc:
            available = list(self._stt)
            raise ProviderNotFoundError(
                f"STT provider {name!r} not found; registered: {available}"
            ) from exc

    def list_stt(self) -> list[str]:
        """Return sorted names of registered STT providers."""
        return sorted(self._stt)

    # --- TTS ---

    def register_tts(self, name: str, provider: "TTSProvider") -> None:
        """Register a TTS provider. Raises DuplicateProviderError on collision."""
        if not name or not name.strip():
            raise ValueError("provider name must be a non-empty string")
        if name in self._tts:
            raise DuplicateProviderError(f"TTS provider {name!r} is already registered")
        self._tts[name] = provider
        log.info("registered TTS provider: %s (class=%s)", name, type(provider).__name__)

    def get_tts(self, name: str) -> "TTSProvider":
        """Return the named TTS provider. Raises ProviderNotFoundError if missing."""
        try:
            return self._tts[name]
        except KeyError as exc:
            available = list(self._tts)
            raise ProviderNotFoundError(
                f"TTS provider {name!r} not found; registered: {available}"
            ) from exc

    def list_tts(self) -> list[str]:
        """Return sorted names of registered TTS providers."""
        return sorted(self._tts)

    def health_summary(self) -> dict:
        """Return a health-safe summary of registered providers (no secrets)."""
        return {
            "stt_providers": self.list_stt(),
            "tts_providers": self.list_tts(),
            "stt_count": len(self._stt),
            "tts_count": len(self._tts),
        }


# Module-level singleton used by the voice-agent entrypoint.
_registry: SpeechProviderRegistry | None = None


def get_registry() -> SpeechProviderRegistry:
    """Return the module-level registry, creating it on first call."""
    global _registry
    if _registry is None:
        _registry = SpeechProviderRegistry()
    return _registry
