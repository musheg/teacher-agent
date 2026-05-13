from uuid import uuid4

import pytest

from app.core.exceptions import AuthError
from app.core.security import (
    TokenKind,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hashing_roundtrip() -> None:
    h = hash_password("hunter2-rocks")
    assert verify_password("hunter2-rocks", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip() -> None:
    uid = uuid4()
    tok = create_token(subject=uid, kind=TokenKind.ACCESS, extra={"role": "parent"})
    payload = decode_token(tok, expected_kind=TokenKind.ACCESS)
    assert payload["sub"] == str(uid)
    assert payload["role"] == "parent"


def test_jwt_wrong_kind_rejected() -> None:
    tok = create_token(subject=uuid4(), kind=TokenKind.REFRESH)
    with pytest.raises(AuthError):
        decode_token(tok, expected_kind=TokenKind.ACCESS)
