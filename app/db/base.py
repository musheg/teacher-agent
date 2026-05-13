"""Declarative base + common mixins (id, timestamps)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base."""

    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        # CamelCase -> snake_case; ReviewQueueItem -> review_queue_items
        import re

        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        return name + "s" if not name.endswith("s") else name


def _utcnow() -> datetime:
    return datetime.now(UTC)


class UUIDPkMixin:
    """UUID primary key."""

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class TimestampMixin:
    """`created_at` / `updated_at` columns managed by SQLAlchemy."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
