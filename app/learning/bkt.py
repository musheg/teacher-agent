"""Bayesian Knowledge Tracing posterior update."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import bkt_updates
from app.db.models import Mastery, Skill


def _bkt_step(
    p_known: float,
    correct: bool,
    *,
    p_slip: float,
    p_guess: float,
    p_transit: float,
) -> float:
    """Apply one BKT update given an observation."""
    if correct:
        num = p_known * (1 - p_slip)
        den = num + (1 - p_known) * p_guess
    else:
        num = p_known * p_slip
        den = num + (1 - p_known) * (1 - p_guess)
    if den == 0:
        return p_known
    posterior = num / den
    # Transition: chance the student just learned the skill.
    return posterior + (1 - posterior) * p_transit


async def apply_bkt_update(
    session: AsyncSession,
    *,
    child_id: UUID,
    skill_id: UUID,
    correct: bool,
) -> float:
    """Update / insert mastery for (child, skill) and return new p_known."""
    skill = await session.get(Skill, skill_id)
    if skill is None:
        raise ValueError(f"unknown skill {skill_id}")

    mastery = await session.scalar(
        select(Mastery).where(Mastery.child_id == child_id, Mastery.skill_id == skill_id)
    )
    if mastery is None:
        mastery = Mastery(child_id=child_id, skill_id=skill_id, p_known=skill.p_init)
        session.add(mastery)

    mastery.p_known = _bkt_step(
        mastery.p_known,
        correct,
        p_slip=skill.p_slip,
        p_guess=skill.p_guess,
        p_transit=skill.p_transit,
    )
    mastery.attempts += 1
    if correct:
        mastery.correct += 1
    mastery.last_seen_at = datetime.now(UTC)
    bkt_updates.inc()
    return mastery.p_known
