"""STT provider Protocol + result models."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class STTWord(BaseModel):
    word: str
    start_s: float
    end_s: float
    confidence: float | None = None


class STTResult(BaseModel):
    transcript: str
    language_code: str
    words: list[STTWord] = []
    confidence: float | None = None
    is_final: bool = True


class STTProvider(Protocol):
    """Speech-to-text provider interface."""

    async def transcribe(
        self,
        audio: bytes,
        *,
        language: str | None = None,
        sample_rate_hz: int | None = None,
        encoding: str | None = None,
    ) -> STTResult: ...
