"""Session, Turn, Mastery, ReviewQueueItem — runtime + learner state."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPkMixin

if TYPE_CHECKING:
    from app.db.models.content import Skill
    from app.db.models.user import Child


class Session(UUIDPkMixin, TimestampMixin, Base):
    """A learning session (a continuous conversation)."""

    __tablename__ = "sessions"

    child_id: Mapped[UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    locale: Mapped[str] = mapped_column(String(16), default="hy-AM", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    child: Mapped[Child] = relationship(back_populates="sessions")
    turns: Mapped[list[Turn]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Turn.created_at",
    )


class Turn(UUIDPkMixin, TimestampMixin, Base):
    """A single conversational turn with full latency / token / cost metrics."""

    __tablename__ = "turns"

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Inputs / outputs (Armenian + English snapshots; raw text only at DEBUG)
    hy_text_in: Mapped[str | None] = mapped_column(Text, nullable=True)
    en_text_in: Mapped[str | None] = mapped_column(Text, nullable=True)
    en_text_out: Mapped[str | None] = mapped_column(Text, nullable=True)
    hy_text_out: Mapped[str | None] = mapped_column(Text, nullable=True)

    viz_spec: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Latency breakdown (ms)
    stt_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    safety_in_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    translate_in_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    curriculum_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tutor_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    solver_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assessment_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    viz_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    speech_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    translate_out_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    safety_out_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tts_first_byte_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tts_total_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    e2e_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    tokens_in_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_out_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd_est: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    fallbacks: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    agent_path: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    session: Mapped[Session] = relationship(back_populates="turns")


class Mastery(UUIDPkMixin, TimestampMixin, Base):
    """BKT posterior per (child, skill)."""

    __tablename__ = "masteries"

    child_id: Mapped[UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )

    p_known: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    skill: Mapped[Skill] = relationship(lazy="joined")

    __table_args__ = (Index("ix_mastery_child_skill", "child_id", "skill_id", unique=True),)


class ReviewQueueItem(UUIDPkMixin, TimestampMixin, Base):
    """A skill scheduled for spaced repetition review."""

    __tablename__ = "review_queue_items"

    child_id: Mapped[UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    interval_days: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    easiness: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)

    skill: Mapped[Skill] = relationship(lazy="joined")

    __table_args__ = (Index("ix_review_child_skill", "child_id", "skill_id", unique=True),)
