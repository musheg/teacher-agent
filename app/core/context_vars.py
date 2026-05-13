"""Context variables propagated across async tasks for structured logging."""

from __future__ import annotations

from contextvars import ContextVar
from uuid import UUID

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
session_id_var: ContextVar[UUID | None] = ContextVar("session_id", default=None)
child_id_var: ContextVar[UUID | None] = ContextVar("child_id", default=None)
parent_id_var: ContextVar[UUID | None] = ContextVar("parent_id", default=None)
user_role_var: ContextVar[str | None] = ContextVar("user_role", default=None)


def set_request_context(
    *,
    request_id: str | None = None,
    session_id: UUID | None = None,
    child_id: UUID | None = None,
    parent_id: UUID | None = None,
    user_role: str | None = None,
) -> None:
    """Set context vars (only the ones provided)."""
    if request_id is not None:
        request_id_var.set(request_id)
    if session_id is not None:
        session_id_var.set(session_id)
    if child_id is not None:
        child_id_var.set(child_id)
    if parent_id is not None:
        parent_id_var.set(parent_id)
    if user_role is not None:
        user_role_var.set(user_role)


def get_request_context() -> dict[str, object]:
    """Snapshot the current context for logging."""
    return {
        "request_id": request_id_var.get(),
        "session_id": str(session_id_var.get()) if session_id_var.get() else None,
        "child_id": str(child_id_var.get()) if child_id_var.get() else None,
        "parent_id": str(parent_id_var.get()) if parent_id_var.get() else None,
        "user_role": user_role_var.get(),
    }
