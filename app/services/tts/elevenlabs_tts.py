"""ElevenLabs Multilingual v2 streaming TTS."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx

from app.core.logging import get_logger
from app.core.metrics import tts_first_byte
from app.settings import get_settings

_log = get_logger("tts.elevenlabs")


class ElevenLabsTTS:
    """Streams MP3 from ElevenLabs."""

    audio_mime = "audio/mpeg"

    async def synthesize(
        self,
        text: str,
        *,
        locale: str = "hy-AM",
        voice: str | None = None,
    ) -> AsyncIterator[bytes]:
        settings = get_settings()
        if not settings.elevenlabs_api_key or not settings.elevenlabs_voice_id:
            raise RuntimeError("ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID not configured")

        voice_id = voice or settings.elevenlabs_voice_id
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
        headers = {
            "xi-api-key": settings.elevenlabs_api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.4, "similarity_boost": 0.75},
        }

        start = asyncio.get_running_loop().time()
        first = False
        async with (
            httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client,
            client.stream("POST", url, json=payload, headers=headers) as resp,
        ):
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(chunk_size=4096):
                if not first:
                    ttfb = int((asyncio.get_running_loop().time() - start) * 1000)
                    tts_first_byte.labels(provider="elevenlabs").observe(ttfb)
                    _log.info(
                        "tts_first_byte",
                        provider="elevenlabs",
                        voice=voice_id,
                        duration_ms=ttfb,
                    )
                    first = True
                if chunk:
                    yield chunk
