"""Example API routes. Register with the main app as needed."""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/")
async def api_root() -> dict[str, str]:
    """API info."""
    return {"message": "API v1"}
