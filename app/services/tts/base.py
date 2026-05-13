"""TTS provider Protocol and shared types."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol


class TTSProvider(Protocol):
    """Streaming text-to-speech provider interface.

    Implementations must return an async iterator that yields raw audio bytes
    (whatever format the provider emits — the caller forwards bytes verbatim to
    the client which knows the content type from `audio_mime`).
    """

    audio_mime: str
    """The MIME type of the chunks this provider yields (e.g. 'audio/mpeg')."""

    def synthesize(
        self,
        text: str,
        *,
        locale: str = "hy-AM",
        voice: str | None = None,
    ) -> AsyncIterator[bytes]: ...
