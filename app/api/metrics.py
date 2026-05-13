"""Prometheus metrics endpoint (admin-only)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.deps import require_admin
from app.core.metrics import REGISTRY
from app.db.models import User

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/metrics")
async def metrics(_user: Annotated[User, Depends(require_admin)]) -> Response:
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
