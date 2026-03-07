"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api import routes

app = FastAPI(
    title="Teacher Agents",
    description="API for teacher agents",
    version="0.1.0",
)


@app.get("/")
async def root() -> dict[str, str]:
    """Health check / root endpoint."""
    return {"status": "ok", "message": "Teacher Agents API"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


app.include_router(routes.router)
