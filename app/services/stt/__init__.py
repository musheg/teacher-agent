"""Speech-to-text providers."""

from app.services.stt.base import STTProvider, STTResult, STTWord
from app.services.stt.google import GoogleSTT

__all__ = ["GoogleSTT", "STTProvider", "STTResult", "STTWord", "get_stt_provider"]


def get_stt_provider() -> STTProvider:
    """Return the configured STT provider (currently Google only)."""
    return GoogleSTT()  # type: ignore[return-value]
