"""FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth as auth_api
from app.api import ws as ws_api
from app.api.middleware import request_id_middleware
from app.core.bootstrap import ensure_admin_user
from app.core.logging import configure_logging, get_logger
from app.db.session import dispose_engine
from app.settings import get_settings

configure_logging()
_log = get_logger("main")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _log.info("app_starting", env=settings.app_env, service=settings.service_name)
    try:
        await ensure_admin_user()
    except Exception as e:
        _log.warning("admin_bootstrap_skipped", error=str(e))
    yield
    await dispose_engine()
    _log.info("app_stopped")


app = FastAPI(
    title="Teacher Agents",
    description="Voice-first multi-agent Armenian math tutor",
    version="0.1.0",
    lifespan=lifespan,
)

app.middleware("http")(request_id_middleware)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "service": "teacher-agents"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


app.include_router(auth_api.router)
app.include_router(ws_api.router)

# Admin + progress routers registered below after they are implemented.
try:
    from app.api import admin as admin_api

    app.include_router(admin_api.router)
except ImportError:
    pass

try:
    from app.api import progress as progress_api

    app.include_router(progress_api.router)
except ImportError:
    pass

try:
    from app.api import parent as parent_api

    app.include_router(parent_api.router)
except ImportError:
    pass

try:
    from app.api import metrics as metrics_api

    app.include_router(metrics_api.router)
except ImportError:
    pass
