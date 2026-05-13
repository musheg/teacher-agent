"""HTTP-level smoke tests using FastAPI's TestClient (no live DB)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    with TestClient(app) as c:
        r = c.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "healthy"}


def test_root() -> None:
    with TestClient(app) as c:
        r = c.get("/")
        assert r.status_code == 200
        assert r.json()["service"] == "teacher-agents"


def test_admin_requires_auth() -> None:
    with TestClient(app) as c:
        r = c.get("/api/admin/age-bands")
        assert r.status_code in (401, 422)  # depends on FastAPI strictness


def test_openapi_lists_routes() -> None:
    with TestClient(app) as c:
        spec = c.get("/openapi.json").json()
        paths = list(spec["paths"].keys())
        for expected in (
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/me",
            "/api/admin/age-bands",
            "/api/parent/children",
            "/api/progress/{child_id}",
        ):
            assert expected in paths, expected
