"""Request-ID middleware that propagates X-Request-Id into contextvars and logs."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from ulid import ULID

from app.core.context_vars import request_id_var, set_request_context
from app.core.logging import get_logger

_log = get_logger("api.request")


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    incoming = request.headers.get("X-Request-Id")
    request_id = incoming if incoming else str(ULID())
    set_request_context(request_id=request_id)
    request.state.request_id = request_id

    start = time.perf_counter()
    response: Response | None = None
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        _log.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=status_code,
            duration_ms=duration_ms,
        )
        if response is not None:
            response.headers["X-Request-Id"] = request_id
        # Reset is unnecessary — request finished.
        request_id_var.set(None)
