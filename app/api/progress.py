"""Per-child progress (mastery + due reviews)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.db.models import Child, Mastery, ReviewQueueItem

router = APIRouter(prefix="/api/progress", tags=["progress"])


class MasteryItem(BaseModel):
    skill_id: UUID
    skill_code: str
    skill_name: str
    p_known: float
    attempts: int
    correct: int


class ReviewItem(BaseModel):
    skill_id: UUID
    skill_code: str
    due_at: str
    failure_count: int
    last_outcome: str | None


class ProgressOut(BaseModel):
    child_id: UUID
    masteries: list[MasteryItem]
    due_reviews: list[ReviewItem]


@router.get("/{child_id}", response_model=ProgressOut)
async def child_progress(child_id: UUID, user: CurrentUser, session: DB) -> ProgressOut:
    child = await session.get(Child, child_id)
    if child is None or child.parent_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="child not found")

    rows = await session.scalars(select(Mastery).where(Mastery.child_id == child_id))
    masteries = [
        MasteryItem(
            skill_id=m.skill_id,
            skill_code=m.skill.code,
            skill_name=m.skill.name,
            p_known=m.p_known,
            attempts=m.attempts,
            correct=m.correct,
        )
        for m in rows
    ]

    rev = await session.scalars(
        select(ReviewQueueItem)
        .where(ReviewQueueItem.child_id == child_id)
        .order_by(ReviewQueueItem.due_at)
    )
    reviews = [
        ReviewItem(
            skill_id=r.skill_id,
            skill_code=r.skill.code,
            due_at=r.due_at.isoformat(),
            failure_count=r.failure_count,
            last_outcome=r.last_outcome,
        )
        for r in rev
    ]
    return ProgressOut(child_id=child_id, masteries=masteries, due_reviews=reviews)
