"""Authentication routes: parent register / login / refresh / child token issuance."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.api.schemas import (
    AccessToken,
    ChildCreateRequest,
    ChildOut,
    RefreshRequest,
    RegisterParentRequest,
    TokenPair,
    UserOut,
)
from app.core.exceptions import AuthError
from app.core.logging import get_logger
from app.core.security import TokenKind, create_token, decode_token, hash_password, verify_password
from app.db.models import User, UserRole
from app.db.models.user import Child

router = APIRouter(prefix="/api/auth", tags=["auth"])
_log = get_logger("auth")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_parent(payload: RegisterParentRequest, session: DB) -> User:
    existing = await session.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.PARENT,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    _log.info("parent_registered", email="[redacted]")
    return user


@router.post("/login", response_model=TokenPair)
async def login(
    session: DB,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenPair:
    user = await session.scalar(select(User).where(User.email == form.username))
    if user is None or not verify_password(form.password, user.password_hash) or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access = create_token(subject=user.id, kind=TokenKind.ACCESS, extra={"role": user.role.value})
    refresh = create_token(subject=user.id, kind=TokenKind.REFRESH)
    _log.info("login_ok", user_id=str(user.id), role=user.role.value)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=AccessToken)
async def refresh(payload: RefreshRequest, session: DB) -> AccessToken:
    try:
        data = decode_token(payload.refresh_token, expected_kind=TokenKind.REFRESH)
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    user = await session.get(User, UUID(data["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    access = create_token(subject=user.id, kind=TokenKind.ACCESS, extra={"role": user.role.value})
    return AccessToken(access_token=access)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user


@router.post("/children/{child_id}/token", response_model=AccessToken)
async def issue_child_token(child_id: UUID, user: CurrentUser, session: DB) -> AccessToken:
    child = await session.get(Child, child_id)
    if child is None or child.parent_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="child not found")
    token = create_token(
        subject=child.id,
        kind=TokenKind.CHILD,
        extra={"parent_id": str(user.id), "locale": child.locale},
    )
    _log.info("child_token_issued", child_id=str(child.id))
    return AccessToken(access_token=token)


@router.post("/children", response_model=ChildOut, status_code=status.HTTP_201_CREATED)
async def create_child(
    payload: ChildCreateRequest,
    user: CurrentUser,
    session: DB,
) -> Child:
    """Create a child profile under the current parent."""
    child = Child(
        parent_id=user.id,
        display_name=payload.display_name,
        birthdate=payload.birthdate,
        grade=payload.grade,
        locale=payload.locale,
        preferences=payload.preferences,
    )
    session.add(child)
    await session.commit()
    await session.refresh(child)
    return child


@router.get("/children", response_model=list[ChildOut])
async def list_children(user: CurrentUser, session: DB) -> list[Child]:
    rows = await session.scalars(
        select(Child).where(Child.parent_id == user.id).order_by(Child.created_at)
    )
    return list(rows)
