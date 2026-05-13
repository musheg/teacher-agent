"""Auth & role-checked FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context_vars import set_request_context
from app.core.exceptions import AuthError
from app.core.security import TokenKind, decode_token
from app.db.models import Child, User, UserRole
from app.db.session import get_sessionmaker

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def db_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


DB = Annotated[AsyncSession, Depends(db_session)]


async def _user_from_token(token: str | None, session: AsyncSession) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(token, expected_kind=TokenKind.ACCESS)
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e

    user_id = UUID(payload["sub"])
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user not found or inactive",
        )
    set_request_context(parent_id=user.id, user_role=user.role.value)
    return user


async def current_user(
    session: DB,
    token: Annotated[str | None, Depends(oauth2)],
) -> User:
    return await _user_from_token(token, session)


CurrentUser = Annotated[User, Depends(current_user)]


def require_role(*roles: UserRole):
    """Build a dependency that enforces one of the listed roles."""

    async def _checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"requires role: {[r.value for r in roles]}",
            )
        return user

    return _checker


require_parent = require_role(UserRole.PARENT, UserRole.ADMIN)
require_admin = require_role(UserRole.ADMIN)


async def child_from_token(
    session: DB,
    token: Annotated[str | None, Depends(oauth2)],
) -> Child:
    """Resolve a child JWT (issued by a parent) into a Child record."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing token")
    try:
        payload = decode_token(token, expected_kind=TokenKind.CHILD)
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    child_id = UUID(payload["sub"])
    child = await session.get(Child, child_id)
    if child is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="child not found")
    set_request_context(child_id=child.id, parent_id=child.parent_id, user_role="child")
    return child


CurrentChild = Annotated[Child, Depends(child_from_token)]
