"""Parent dashboard endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.db.models import Child, Mastery, ReviewQueueItem
from app.db.models.progress import Session as SessionModel
from app.db.models.progress import Turn

router = APIRouter(prefix="/api/parent", tags=["parent"])


class ChildSummary(BaseModel):
    id: UUID
    display_name: str
    grade: int | None
    locale: str
    weekly_minutes: float


class MasteryCell(BaseModel):
    skill_code: str
    skill_name: str
    p_known: float
    last_seen_at: datetime | None


class StumbleItem(BaseModel):
    skill_code: str
    skill_name: str
    failure_count: int
    due_at: datetime
    last_outcome: str | None


class SessionItem(BaseModel):
    id: UUID
    started_at: datetime
    ended_at: datetime | None
    turn_count: int


async def _get_child(session, user_id: UUID, child_id: UUID) -> Child:
    child = await session.get(Child, child_id)
    if child is None or child.parent_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="child not found")
    return child


@router.get("/children", response_model=list[ChildSummary])
async def list_children(user: CurrentUser, session: DB) -> list[ChildSummary]:
    rows = await session.scalars(select(Child).where(Child.parent_id == user.id))
    out: list[ChildSummary] = []
    week_start = datetime.now(UTC) - timedelta(days=7)
    for c in rows:
        sessions = await session.scalars(
            select(SessionModel).where(
                SessionModel.child_id == c.id,
                SessionModel.started_at >= week_start,
            )
        )
        total = 0.0
        for s in sessions:
            end = s.ended_at or datetime.now(UTC)
            total += (end - s.started_at).total_seconds() / 60.0
        out.append(
            ChildSummary(
                id=c.id,
                display_name=c.display_name,
                grade=c.grade,
                locale=c.locale,
                weekly_minutes=round(total, 1),
            )
        )
    return out


@router.get("/children/{child_id}/mastery", response_model=list[MasteryCell])
async def child_mastery(child_id: UUID, user: CurrentUser, session: DB) -> list[MasteryCell]:
    await _get_child(session, user.id, child_id)
    rows = await session.scalars(select(Mastery).where(Mastery.child_id == child_id))
    return [
        MasteryCell(
            skill_code=m.skill.code,
            skill_name=m.skill.name,
            p_known=m.p_known,
            last_seen_at=m.last_seen_at,
        )
        for m in rows
    ]


@router.get("/children/{child_id}/stumbles", response_model=list[StumbleItem])
async def child_stumbles(child_id: UUID, user: CurrentUser, session: DB) -> list[StumbleItem]:
    await _get_child(session, user.id, child_id)
    rows = await session.scalars(
        select(ReviewQueueItem)
        .where(ReviewQueueItem.child_id == child_id)
        .order_by(ReviewQueueItem.failure_count.desc())
        .limit(5)
    )
    return [
        StumbleItem(
            skill_code=r.skill.code,
            skill_name=r.skill.name,
            failure_count=r.failure_count,
            due_at=r.due_at,
            last_outcome=r.last_outcome,
        )
        for r in rows
    ]


@router.get("/children/{child_id}/sessions", response_model=list[SessionItem])
async def child_sessions(child_id: UUID, user: CurrentUser, session: DB) -> list[SessionItem]:
    await _get_child(session, user.id, child_id)
    rows = await session.scalars(
        select(SessionModel)
        .where(SessionModel.child_id == child_id)
        .order_by(SessionModel.started_at.desc())
        .limit(20)
    )
    out: list[SessionItem] = []
    for s in rows:
        cnt = await session.scalar(
            select(Turn.id).where(Turn.session_id == s.id).with_only_columns(Turn.id).limit(1)
        )
        # Count turns properly via separate query
        from sqlalchemy import func

        count = await session.scalar(select(func.count(Turn.id)).where(Turn.session_id == s.id))
        _ = cnt
        out.append(
            SessionItem(
                id=s.id,
                started_at=s.started_at,
                ended_at=s.ended_at,
                turn_count=count or 0,
            )
        )
    return out
