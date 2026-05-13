"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("POSTGRES_DSN", "postgresql+asyncpg://teacher:teacher@localhost/teacher")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(autouse=True)
def _configure_logging() -> None:
    from app.core.logging import configure_logging

    configure_logging()
