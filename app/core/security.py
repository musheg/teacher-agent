"""Password hashing and JWT helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.exceptions import AuthError
from app.settings import get_settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenKind(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    CHILD = "child"


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _pwd.verify(password, hashed)
    except ValueError:
        return False


def create_token(
    *,
    subject: UUID | str,
    kind: TokenKind,
    extra: dict[str, Any] | None = None,
    expires_in: timedelta | None = None,
) -> str:
    settings = get_settings()
    if expires_in is None:
        if kind == TokenKind.ACCESS:
            expires_in = timedelta(minutes=settings.jwt_access_ttl_minutes)
        elif kind == TokenKind.REFRESH:
            expires_in = timedelta(days=settings.jwt_refresh_ttl_days)
        else:
            # Child tokens are short-lived — single session.
            expires_in = timedelta(hours=8)

    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "kind": kind.value,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_in).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, *, expected_kind: TokenKind | None = None) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise AuthError(f"invalid token: {e}") from e
    if expected_kind is not None and payload.get("kind") != expected_kind.value:
        raise AuthError(f"expected {expected_kind.value} token, got {payload.get('kind')}")
    return payload
