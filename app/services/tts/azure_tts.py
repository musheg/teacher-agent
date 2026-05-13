"""Azure Neural TTS (supports native hy-AM voices)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx

from app.core.logging import get_logger
from app.core.metrics import tts_first_byte
from app.settings import get_settings

_log = get_logger("tts.azure")


class AzureTTS:
    """Calls Azure Cognitive Services TTS REST API with streaming response."""

    audio_mime = "audio/mpeg"

    async def synthesize(
        self,
        text: str,
        *,
        locale: str = "hy-AM",
        voice: str | None = None,
    ) -> AsyncIterator[bytes]:
        settings = get_settings()
        if not settings.azure_speech_key or not settings.azure_speech_region:
            raise RuntimeError("AZURE_SPEECH_KEY / AZURE_SPEECH_REGION not configured")

        voice_name = voice or settings.azure_tts_voice
        endpoint = (
            f"https://{settings.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": settings.azure_speech_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
            "User-Agent": "teacher-agents",
        }
        ssml = (
            f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            f'xml:lang="{locale}">'
            f'<voice name="{voice_name}">{_escape(text)}</voice>'
            "</speak>"
        )

        start = asyncio.get_running_loop().time()
        first = False
        async with (
            httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client,
            client.stream("POST", endpoint, content=ssml, headers=headers) as resp,
        ):
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(chunk_size=4096):
                if not first:
                    ttfb = int((asyncio.get_running_loop().time() - start) * 1000)
                    tts_first_byte.labels(provider="azure").observe(ttfb)
                    _log.info(
                        "tts_first_byte",
                        provider="azure",
                        voice=voice_name,
                        duration_ms=ttfb,
                    )
                    first = True
                if chunk:
                    yield chunk


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
