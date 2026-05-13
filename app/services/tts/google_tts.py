"""Google Cloud TTS — English-only fallback (does NOT support hy-AM)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.core.logging import get_logger
from app.core.metrics import tts_first_byte
from app.settings import get_settings

_log = get_logger("tts.google")


class GoogleTTS:
    """Streams MP3 from Google Cloud Text-to-Speech.

    NOTE: As of 2026, Google TTS does not support Armenian. Use only for
    English content (e.g., fallback voice for English explanations).
    """

    audio_mime = "audio/mpeg"

    def __init__(self) -> None:
        self._client = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            from google.cloud import texttospeech_v1 as tts
        except (ImportError, AttributeError) as e:  # pragma: no cover
            raise RuntimeError(
                "google-cloud-texttospeech is not installed; "
                "switch TTS_PROVIDER or install the package."
            ) from e
        self._client = tts.TextToSpeechAsyncClient()

    async def synthesize(
        self,
        text: str,
        *,
        locale: str = "en-US",
        voice: str | None = None,
    ) -> AsyncIterator[bytes]:
        settings = get_settings()
        self._ensure_client()
        from google.cloud import texttospeech_v1 as tts  # type: ignore[import-untyped,attr-defined]

        synthesis_input = tts.SynthesisInput(text=text)
        params = tts.VoiceSelectionParams(
            language_code=locale,
            name=voice or settings.tts_voice,
        )
        audio_cfg = tts.AudioConfig(audio_encoding=tts.AudioEncoding.MP3)

        start = asyncio.get_running_loop().time()
        assert self._client is not None
        resp = await self._client.synthesize_speech(
            input=synthesis_input, voice=params, audio_config=audio_cfg
        )
        ttfb = int((asyncio.get_running_loop().time() - start) * 1000)
        tts_first_byte.labels(provider="google").observe(ttfb)
        _log.info("tts_first_byte", provider="google", duration_ms=ttfb)
        yield resp.audio_content
