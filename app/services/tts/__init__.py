"""TTS provider factory + clause splitter."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator

from app.core.logging import get_logger
from app.services.tts.azure_tts import AzureTTS
from app.services.tts.base import TTSProvider
from app.services.tts.elevenlabs_tts import ElevenLabsTTS
from app.services.tts.google_tts import GoogleTTS
from app.services.tts.openai_tts import OpenAITTS
from app.settings import get_settings

_log = get_logger("tts.factory")

_REGISTRY: dict[str, type] = {
    "openai": OpenAITTS,
    "azure": AzureTTS,
    "elevenlabs": ElevenLabsTTS,
    "google": GoogleTTS,
}


def get_tts_provider(name: str | None = None) -> TTSProvider:
    settings = get_settings()
    key = (name or settings.tts_provider).lower()
    cls = _REGISTRY.get(key)
    if cls is None:
        raise ValueError(f"unknown TTS_PROVIDER: {key}")
    _log.info("tts_provider_selected", provider=key)
    return cls()  # type: ignore[no-any-return]


# Split on sentence-terminal punctuation (Armenian + Latin) plus ellipsis / question / exclamation.
_CLAUSE_SPLIT_RE = re.compile(r"(?<=[\.\?!։:])\s+|(?<=[\.\?!])\n+")


def split_into_clauses(text: str, *, max_chars: int = 180) -> list[str]:
    """Split `text` into TTS-friendly clauses.

    Each clause is at most ~`max_chars` long; if a sentence is too long we
    further split on commas/Armenian comma.
    """
    text = text.strip()
    if not text:
        return []

    raw_chunks = [c.strip() for c in _CLAUSE_SPLIT_RE.split(text) if c.strip()]
    out: list[str] = []
    for chunk in raw_chunks:
        if len(chunk) <= max_chars:
            out.append(chunk)
            continue
        parts = re.split(r"(?<=[,،՝])\s+", chunk)
        buf = ""
        for p in parts:
            if len(buf) + len(p) + 1 <= max_chars:
                buf = (buf + " " + p).strip()
            else:
                if buf:
                    out.append(buf)
                buf = p
        if buf:
            out.append(buf)
    return out


async def synthesize_clause_stream(
    provider: TTSProvider,
    clauses: list[str],
    *,
    locale: str = "hy-AM",
    voice: str | None = None,
) -> AsyncIterator[tuple[int, bytes]]:
    """Iterate (seq, audio_bytes) for each clause in order.

    Yields the seq for the clause and each chunk as it arrives.
    """
    for seq, clause in enumerate(clauses):
        async for chunk in provider.synthesize(clause, locale=locale, voice=voice):
            yield seq, chunk


__all__ = [
    "AzureTTS",
    "ElevenLabsTTS",
    "GoogleTTS",
    "OpenAITTS",
    "TTSProvider",
    "get_tts_provider",
    "split_into_clauses",
    "synthesize_clause_stream",
]
