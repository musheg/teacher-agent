"""Google Cloud Speech v2 client using Chirp_2 for hy-AM."""

from __future__ import annotations

import asyncio

from app.core.logging import get_logger
from app.core.metrics import stt_latency
from app.core.resilience import resilient
from app.services.stt.base import STTResult, STTWord
from app.settings import get_settings

_log = get_logger("stt.google")


class GoogleSTT:
    """Google Cloud Speech-to-Text v2 client.

    Uses recognize() (synchronous batch) — short audio (<60s) is fine.
    """

    def __init__(self) -> None:
        self._client: object | None = None
        self._recognizer_path: str | None = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        settings = get_settings()
        try:
            from google.api_core import client_options as gco
            from google.cloud import speech_v2
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("google-cloud-speech not installed") from e

        if settings.stt_project_id is None:
            raise RuntimeError("STT_PROJECT_ID is required for Google STT")

        endpoint = (
            f"{settings.stt_location}-speech.googleapis.com"
            if settings.stt_location != "global"
            else "speech.googleapis.com"
        )
        self._client = speech_v2.SpeechAsyncClient(
            client_options=gco.ClientOptions(api_endpoint=endpoint)
        )
        self._recognizer_path = (
            f"projects/{settings.stt_project_id}/locations/{settings.stt_location}/recognizers/_"
        )

    @resilient(upstream="google_stt")
    async def transcribe(
        self,
        audio: bytes,
        *,
        language: str | None = None,
        sample_rate_hz: int | None = None,
        encoding: str | None = None,
    ) -> STTResult:
        """Transcribe a short audio clip and return a structured result."""
        settings = get_settings()
        lang = language or settings.stt_language
        self._ensure_client()

        from google.cloud.speech_v2 import types

        config = types.RecognitionConfig(
            auto_decoding_config=types.AutoDetectDecodingConfig(),
            language_codes=[lang],
            model=settings.stt_model,
            features=types.RecognitionFeatures(
                enable_word_time_offsets=True,
                enable_word_confidence=True,
                enable_automatic_punctuation=True,
            ),
        )
        request = types.RecognizeRequest(
            recognizer=self._recognizer_path,
            config=config,
            content=audio,
        )

        loop = asyncio.get_running_loop()
        start = loop.time()
        assert self._client is not None
        response = await self._client.recognize(request=request)  # type: ignore[attr-defined]
        elapsed_ms = int((loop.time() - start) * 1000)
        stt_latency.labels(provider="google", model=settings.stt_model).observe(elapsed_ms)

        words: list[STTWord] = []
        transcript_chunks: list[str] = []
        confidences: list[float] = []
        for result in response.results:
            if not result.alternatives:
                continue
            alt = result.alternatives[0]
            transcript_chunks.append(alt.transcript)
            if alt.confidence:
                confidences.append(alt.confidence)
            for w in alt.words:
                words.append(
                    STTWord(
                        word=w.word,
                        start_s=w.start_offset.total_seconds() if w.start_offset else 0.0,
                        end_s=w.end_offset.total_seconds() if w.end_offset else 0.0,
                        confidence=w.confidence or None,
                    )
                )

        transcript = " ".join(transcript_chunks).strip()
        _log.info(
            "stt_complete",
            provider="google",
            model=settings.stt_model,
            language=lang,
            transcript_len=len(transcript),
            duration_ms=elapsed_ms,
        )
        return STTResult(
            transcript=transcript,
            language_code=lang,
            words=words,
            confidence=(sum(confidences) / len(confidences)) if confidences else None,
        )
