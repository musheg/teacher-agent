"""structlog JSON logging with PII redaction and request-context auto-binding."""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.core.context_vars import get_request_context
from app.settings import get_settings

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b")
_PHONE_RE = re.compile(r"\b\+?\d[\d\s\-().]{7,}\d\b")
_REDACTABLE_KEYS: frozenset[str] = frozenset(
    {
        "email",
        "phone",
        "password",
        "secret",
        "token",
        "authorization",
        "child_name",
        "parent_name",
        "first_name",
        "last_name",
        "full_name",
    }
)


def _redact_value(value: object) -> object:
    if isinstance(value, str):
        v = _EMAIL_RE.sub("[redacted-email]", value)
        v = _PHONE_RE.sub("[redacted-phone]", v)
        return v
    return value


def _pii_redactor(_logger: Any, _name: str, event_dict: EventDict) -> EventDict:
    """Redact PII in known sensitive keys and scan strings for emails/phones."""
    for key in list(event_dict.keys()):
        if key.lower() in _REDACTABLE_KEYS:
            event_dict[key] = "[redacted]"
        else:
            event_dict[key] = _redact_value(event_dict[key])
    return event_dict


def _bind_request_context(_logger: Any, _name: str, event_dict: EventDict) -> EventDict:
    """Inject request/session/child IDs from contextvars."""
    ctx = get_request_context()
    for k, v in ctx.items():
        event_dict.setdefault(k, v)
    return event_dict


def _ensure_stable_schema(_logger: Any, _name: str, event_dict: EventDict) -> EventDict:
    """Guarantee a stable set of keys on every record (null when missing)."""
    settings = get_settings()
    schema_keys: tuple[str, ...] = (
        "service",
        "env",
        "request_id",
        "session_id",
        "child_id",
        "parent_id",
        "user_role",
        "agent",
        "node",
        "model",
        "provider",
        "duration_ms",
        "tokens_in",
        "tokens_out",
        "cost_usd_est",
    )
    event_dict.setdefault("service", settings.service_name)
    event_dict.setdefault("env", settings.app_env)
    for key in schema_keys:
        event_dict.setdefault(key, None)
    return event_dict


def _strip_color(_logger: Any, _name: str, event_dict: EventDict) -> EventDict:
    return event_dict


def configure_logging() -> None:
    """Configure structlog and intercept stdlib logging.

    Idempotent — safe to call multiple times.
    """
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
        _bind_request_context,
        _pii_redactor,
        _ensure_stable_schema,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_format == "json":
        renderer: Processor = structlog.processors.JSONRenderer(sort_keys=True)
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=shared_processors,
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "sqlalchemy.engine"):
        lg = logging.getLogger(noisy)
        lg.handlers = [handler]
        lg.propagate = False
        if noisy == "sqlalchemy.engine":
            lg.setLevel(logging.WARNING)
        else:
            lg.setLevel(level)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a configured logger; safe to call before `configure_logging`."""
    return structlog.get_logger(name or "app")
