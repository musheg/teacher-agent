"""User, Child, and role definitions."""

from __future__ import annotations

import enum
from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPkMixin

if TYPE_CHECKING:
    from app.db.models.progress import Session as SessionModel


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PARENT = "parent"


class User(UUIDPkMixin, TimestampMixin, Base):
    """A registered adult user (admin or parent)."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.PARENT, nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    children: Mapped[list[Child]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Child(UUIDPkMixin, TimestampMixin, Base):
    """A learner profile owned by a parent user."""

    __tablename__ = "children"

    parent_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    birthdate: Mapped[date] = mapped_column(Date, nullable=False)
    grade: Mapped[int | None] = mapped_column(nullable=True)
    locale: Mapped[str] = mapped_column(String(16), default="hy-AM", nullable=False)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    parent: Mapped[User] = relationship(back_populates="children")
    sessions: Mapped[list[SessionModel]] = relationship(
        back_populates="child", cascade="all, delete-orphan"
    )
