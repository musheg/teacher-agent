"""Seed an initial math course for the 5–7 age band.

Run inside the api container::

    docker compose run --rm api python -m app.scripts.seed
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.db.models import AgeBand, Course, Exercise, ExerciseType, Skill, Unit
from app.db.session import get_sessionmaker

configure_logging()
_log = get_logger("seed")


async def seed() -> None:
    async with get_sessionmaker()() as session:
        band = await session.scalar(select(AgeBand).where(AgeBand.name == "5-7"))
        if band is None:
            band = AgeBand(
                name="5-7",
                min_age=5,
                max_age=7,
                description="Early-elementary, concrete reasoning with manipulatives.",
                pedagogy_notes={
                    "tone": "warm, bouncy",
                    "max_sentence_words": 8,
                    "preferred_viz": ["fraction_pie", "number_line"],
                    "session_minutes_target": 15,
                },
            )
            session.add(band)
            await session.flush()
            _log.info("seeded_age_band", name=band.name)

        course = await session.scalar(
            select(Course).where(Course.age_band_id == band.id, Course.subject == "math")
        )
        if course is None:
            course = Course(
                age_band_id=band.id,
                subject="math",
                title="Foundations of Math (Ages 5-7)",
                description="Counting, addition/subtraction up to 20, intro fractions.",
            )
            session.add(course)
            await session.flush()
            _log.info("seeded_course", title=course.title)

        unit_defs: list[tuple[str, list[tuple[str, str]]]] = [
            (
                "Counting",
                [
                    ("count_to_10", "Count from 1 to 10"),
                    ("count_to_20", "Count from 1 to 20"),
                    ("compare_numbers", "Which number is bigger?"),
                ],
            ),
            (
                "Addition & subtraction",
                [
                    ("add_within_10", "Add numbers up to 10"),
                    ("sub_within_10", "Subtract numbers up to 10"),
                    ("word_problems_basic", "Simple word problems"),
                ],
            ),
            (
                "Intro to fractions",
                [
                    ("halves", "Recognize halves"),
                    ("quarters", "Recognize quarters"),
                    ("compare_fractions_basic", "Compare 1/2 vs 1/4"),
                ],
            ),
        ]

        for u_order, (u_name, skills) in enumerate(unit_defs):
            unit = await session.scalar(
                select(Unit).where(Unit.course_id == course.id, Unit.name == u_name)
            )
            if unit is None:
                unit = Unit(course_id=course.id, name=u_name, order_index=u_order)
                session.add(unit)
                await session.flush()
            for s_order, (code, name) in enumerate(skills):
                skill = await session.scalar(
                    select(Skill).where(Skill.unit_id == unit.id, Skill.code == code)
                )
                if skill is None:
                    skill = Skill(
                        unit_id=unit.id,
                        code=code,
                        name=name,
                        order_index=s_order,
                    )
                    session.add(skill)
                    await session.flush()
                    # one sample exercise per skill
                    session.add(
                        Exercise(
                            skill_id=skill.id,
                            type=ExerciseType.SHORT_ANSWER,
                            prompt=f"Practice: {name}",
                            payload={"hint": "Take it slow."},
                            difficulty=1,
                            locale="hy-AM",
                        )
                    )

        await session.commit()
        _log.info("seed_complete")


if __name__ == "__main__":
    asyncio.run(seed())
