"""Curriculum content models: AgeBand, Course, Unit, Skill, Exercise."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPkMixin

if TYPE_CHECKING:
    pass


class AgeBand(UUIDPkMixin, TimestampMixin, Base):
    """A pedagogical age band (e.g. 5–7, 8–11)."""

    __tablename__ = "age_bands"

    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    min_age: Mapped[int] = mapped_column(nullable=False)
    max_age: Mapped[int] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    pedagogy_notes: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    courses: Mapped[list[Course]] = relationship(back_populates="age_band")


class Course(UUIDPkMixin, TimestampMixin, Base):
    """A subject taught for a given age band (e.g. Math for 5–7)."""

    __tablename__ = "courses"

    age_band_id: Mapped[UUID] = mapped_column(
        ForeignKey("age_bands.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    age_band: Mapped[AgeBand] = relationship(back_populates="courses")
    units: Mapped[list[Unit]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Unit.order_index",
    )


class Unit(UUIDPkMixin, TimestampMixin, Base):
    """A unit within a course."""

    __tablename__ = "units"

    course_id: Mapped[UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(default=0, nullable=False)

    course: Mapped[Course] = relationship(back_populates="units")
    skills: Mapped[list[Skill]] = relationship(
        back_populates="unit",
        cascade="all, delete-orphan",
        order_by="Skill.order_index",
    )


class Skill(UUIDPkMixin, TimestampMixin, Base):
    """An atomic teachable skill with BKT priors."""

    __tablename__ = "skills"

    unit_id: Mapped[UUID] = mapped_column(
        ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(default=0, nullable=False)

    # BKT priors
    p_init: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)
    p_transit: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    p_slip: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)
    p_guess: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)

    prerequisites: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )  # list of skill codes

    unit: Mapped[Unit] = relationship(back_populates="skills")
    exercises: Mapped[list[Exercise]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_skills_unit_code", "unit_id", "code", unique=True),)


class ExerciseType(str, enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    FREE_RESPONSE = "free_response"
    DRAG_DROP = "drag_drop"
    SHORT_ANSWER = "short_answer"


class Exercise(UUIDPkMixin, TimestampMixin, Base):
    """A single exercise/problem attached to a skill."""

    __tablename__ = "exercises"

    skill_id: Mapped[UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[ExerciseType] = mapped_column(
        Enum(ExerciseType, name="exercise_type"), nullable=False
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    difficulty: Mapped[int] = mapped_column(default=1, nullable=False)
    locale: Mapped[str] = mapped_column(String(16), default="hy-AM", nullable=False)

    skill: Mapped[Skill] = relationship(back_populates="exercises")
