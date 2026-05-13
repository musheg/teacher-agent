"""SM-2 spaced-repetition scheduling.

Given an outcome (`correct` + a 0–5 quality score), update the review item's
easiness, interval, and `due_at`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ReviewQueueItem


def _sm2(easiness: float, repetitions: int, quality: int) -> tuple[float, int, float]:
    """Return new (easiness, repetitions, interval_days)."""
    if quality < 3:
        # Failed: reset repetitions, short interval.
        new_easiness = max(1.3, easiness - 0.2)
        return new_easiness, 0, 1.0
    new_easiness = max(1.3, easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    if repetitions == 0:
        interval = 1.0
    elif repetitions == 1:
        interval = 6.0
    else:
        interval = 6.0 * new_easiness ** (repetitions - 1)
    return new_easiness, repetitions + 1, interval


async def schedule_review(
    session: AsyncSession,
    *,
    child_id: UUID,
    skill_id: UUID,
    quality: int,
) -> ReviewQueueItem:
    """Insert or update a review queue item given a 0–5 quality outcome."""
    item = await session.scalar(
        select(ReviewQueueItem).where(
            ReviewQueueItem.child_id == child_id,
            ReviewQueueItem.skill_id == skill_id,
        )
    )
    now = datetime.now(UTC)
    if item is None:
        item = ReviewQueueItem(
            child_id=child_id,
            skill_id=skill_id,
            due_at=now + timedelta(days=1),
        )
        session.add(item)

    new_e, new_r, new_i = _sm2(item.easiness, item.repetitions, quality)
    item.easiness = new_e
    item.repetitions = new_r
    item.interval_days = new_i
    item.due_at = now + timedelta(days=new_i)
    item.last_outcome = "ok" if quality >= 3 else "fail"
    if quality < 3:
        item.failure_count += 1
    return item
