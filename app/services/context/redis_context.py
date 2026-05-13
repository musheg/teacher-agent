"""Redis-backed sliding-window conversation context with rolling summary."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

import redis.asyncio as aioredis
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.settings import get_settings

_log = get_logger("context")

Role = Literal["child", "tutor", "system"]


class ContextTurn(BaseModel):
    """A single turn stored in Redis."""

    role: Role
    text: str = ""
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tokens_est: int = 0
    meta: dict = Field(default_factory=dict)


def _estimate_tokens(text: str) -> int:
    """Cheap token estimate (~4 chars/token)."""
    return max(1, len(text) // 4)


class ContextManager:
    """Sliding-window context with overflow-triggered summarization.

    Layout per session:
      - `ctx:{session_id}` — Redis list (left = oldest) of JSON-serialized turns.
      - `ctx_sum:{session_id}` — rolling summary string of evicted turns.
    """

    def __init__(self, client: aioredis.Redis | None = None) -> None:
        self._client = client

    @classmethod
    def from_settings(cls) -> ContextManager:
        settings = get_settings()
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        return cls(client)

    @property
    def client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(get_settings().redis_url, decode_responses=True)
        return self._client

    @staticmethod
    def _key(session_id: UUID) -> str:
        return f"ctx:{session_id}"

    @staticmethod
    def _sum_key(session_id: UUID) -> str:
        return f"ctx_sum:{session_id}"

    async def append(self, session_id: UUID, turn: ContextTurn) -> None:
        if turn.tokens_est == 0:
            turn.tokens_est = _estimate_tokens(turn.text)
        await self.client.rpush(self._key(session_id), turn.model_dump_json())  # type: ignore[misc]

    async def get_summary(self, session_id: UUID) -> str:
        val = await self.client.get(self._sum_key(session_id))
        return val or ""

    async def set_summary(self, session_id: UUID, summary: str) -> None:
        await self.client.set(self._sum_key(session_id), summary)

    async def get_window(self, session_id: UUID, limit: int | None = None) -> list[ContextTurn]:
        settings = get_settings()
        n = limit if limit is not None else settings.context_max_turns
        raw = await self.client.lrange(self._key(session_id), -n, -1)  # type: ignore[misc]
        return [ContextTurn.model_validate_json(r) for r in raw]

    async def get_full(self, session_id: UUID) -> list[ContextTurn]:
        raw = await self.client.lrange(self._key(session_id), 0, -1)  # type: ignore[misc]
        return [ContextTurn.model_validate_json(r) for r in raw]

    async def estimate_tokens(self, session_id: UUID) -> int:
        turns = await self.get_full(session_id)
        return sum(t.tokens_est for t in turns)

    async def maybe_summarize(
        self,
        session_id: UUID,
        *,
        summarizer: Summarizer,
    ) -> bool:
        """Compress oldest half into the rolling summary when over threshold.

        Returns True if a summarization was performed.
        """
        settings = get_settings()
        all_turns = await self.get_full(session_id)
        total = sum(t.tokens_est for t in all_turns)
        if total < settings.context_summary_threshold_tokens or len(all_turns) < 6:
            return False

        cutoff = len(all_turns) // 2
        old_turns = all_turns[:cutoff]
        kept = all_turns[cutoff:]
        existing_summary = await self.get_summary(session_id)

        new_summary = await summarizer(
            existing_summary=existing_summary,
            turns=old_turns,
        )
        await self.set_summary(session_id, new_summary)
        await self.client.delete(self._key(session_id))
        if kept:
            await self.client.rpush(  # type: ignore[misc]
                self._key(session_id),
                *[t.model_dump_json() for t in kept],
            )
        _log.info(
            "context_summarized",
            session_id=str(session_id),
            kept=len(kept),
            evicted=len(old_turns),
            new_summary_len=len(new_summary),
        )
        return True

    async def reset(self, session_id: UUID) -> None:
        await self.client.delete(self._key(session_id), self._sum_key(session_id))

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()


class Summarizer:
    """Callable protocol for the summarization function.

    Kept structural so tests can pass a callable; the real implementation lives
    in `app/agents/summarizer.py`.
    """

    async def __call__(
        self, *, existing_summary: str, turns: list[ContextTurn]
    ) -> str:  # pragma: no cover
        raise NotImplementedError


def serialize_for_prompt(summary: str, turns: list[ContextTurn]) -> str:
    """Render summary + recent turns into a single prompt block."""
    parts: list[str] = []
    if summary:
        parts.append(f"[Prior conversation summary]\n{summary}")
    parts.append("[Recent turns]")
    for t in turns:
        parts.append(f"- {t.role}: {t.text}")
    return "\n".join(parts)


__all__ = ["ContextManager", "ContextTurn", "Summarizer", "serialize_for_prompt"]
