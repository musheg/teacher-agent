"""Startup bootstrap helpers (admin user seeding)."""

from __future__ import annotations

from sqlalchemy import select

from app.core.logging import get_logger
from app.core.security import hash_password
from app.db.models import User, UserRole
from app.db.session import get_sessionmaker
from app.settings import get_settings

_log = get_logger("bootstrap")


async def ensure_admin_user() -> None:
    """Create an admin user from env if `CREATE_ADMIN_EMAIL/PASSWORD` are set."""
    settings = get_settings()
    if not settings.create_admin_email or not settings.create_admin_password:
        return

    async with get_sessionmaker()() as session:
        existing = await session.scalar(
            select(User).where(User.email == settings.create_admin_email)
        )
        if existing is not None:
            if existing.role != UserRole.ADMIN:
                existing.role = UserRole.ADMIN
                await session.commit()
                _log.info("admin_promoted", user_id=str(existing.id))
            return
        user = User(
            email=settings.create_admin_email,
            password_hash=hash_password(settings.create_admin_password),
            role=UserRole.ADMIN,
            full_name="Bootstrap Admin",
        )
        session.add(user)
        await session.commit()
        _log.info("admin_created", user_id=str(user.id))
