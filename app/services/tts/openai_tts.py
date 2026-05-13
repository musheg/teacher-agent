"""OpenAI streaming TTS using `gpt-4o-mini-tts` (or equivalent)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.core.logging import get_logger
from app.core.metrics import tts_first_byte
from app.settings import get_settings

_log = get_logger("tts.openai")


class OpenAITTS:
    """Streams MP3 audio from OpenAI's TTS API."""

    audio_mime = "audio/mpeg"

    def __init__(self, client: AsyncOpenAI | None = None) -> None:
        self._client = client or AsyncOpenAI(api_key=get_settings().openai_api_key)

    async def synthesize(
        self,
        text: str,
        *,
        locale: str = "hy-AM",
        voice: str | None = None,
    ) -> AsyncIterator[bytes]:
        settings = get_settings()
        first_byte_logged = False
        start = asyncio.get_running_loop().time()
        used_voice = voice or settings.tts_voice
        used_model = settings.openai_tts_model

        async with self._client.audio.speech.with_streaming_response.create(
            model=used_model,
            voice=used_voice,
            input=text,
            response_format="mp3",
        ) as response:
            async for chunk in response.iter_bytes(chunk_size=4096):
                if not first_byte_logged:
                    ttfb = int((asyncio.get_running_loop().time() - start) * 1000)
                    tts_first_byte.labels(provider="openai").observe(ttfb)
                    _log.info(
                        "tts_first_byte",
                        provider="openai",
                        model=used_model,
                        voice=used_voice,
                        duration_ms=ttfb,
                    )
                    first_byte_logged = True
                if chunk:
                    yield chunk
