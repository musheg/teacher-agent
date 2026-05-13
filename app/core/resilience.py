"""Resilience helpers: timeout, retry, circuit breaker, and fallback chains."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import wraps
from typing import ParamSpec, TypeVar

from tenacity import (
    AsyncRetrying,
    RetryError,
    stop_after_attempt,
    wait_exponential,
)

from app.core.exceptions import (
    AllFallbacksFailedError,
    CircuitOpenError,
    UpstreamError,
)
from app.core.logging import get_logger
from app.core.metrics import TurnMetrics, llm_errors
from app.settings import get_settings

P = ParamSpec("P")
T = TypeVar("T")

_log = get_logger("resilience")


@dataclass
class _BreakerState:
    failures: int = 0
    opened_at: float | None = None


class CircuitBreaker:
    """Per-upstream circuit breaker.

    Opens after `threshold` consecutive failures; stays open for `cooldown` seconds.
    """

    def __init__(self, threshold: int = 5, cooldown: float = 30.0) -> None:
        self.threshold = threshold
        self.cooldown = cooldown
        self._states: dict[str, _BreakerState] = {}

    def _state(self, upstream: str) -> _BreakerState:
        return self._states.setdefault(upstream, _BreakerState())

    def is_open(self, upstream: str) -> bool:
        s = self._state(upstream)
        if s.opened_at is None:
            return False
        if time.monotonic() - s.opened_at > self.cooldown:
            s.opened_at = None
            s.failures = 0
            return False
        return True

    def record_success(self, upstream: str) -> None:
        s = self._state(upstream)
        s.failures = 0
        s.opened_at = None

    def record_failure(self, upstream: str) -> None:
        s = self._state(upstream)
        s.failures += 1
        if s.failures >= self.threshold:
            s.opened_at = time.monotonic()
            _log.warning("circuit_opened", upstream=upstream, failures=s.failures)


breaker = CircuitBreaker()


async def call_with_retry(
    fn: Callable[..., Awaitable[T]],
    *args: object,
    upstream: str,
    timeout_s: float | None = None,
    max_attempts: int | None = None,
    **kwargs: object,
) -> T:
    """Call `fn` with timeout + exponential-backoff retry.

    Raises :class:`UpstreamError` on final failure.
    """
    settings = get_settings()
    timeout = timeout_s if timeout_s is not None else float(settings.llm_timeout_seconds)
    attempts = max_attempts if max_attempts is not None else settings.llm_max_retries + 1

    if breaker.is_open(upstream):
        llm_errors.labels(provider=upstream, model="", reason="circuit_open").inc()
        raise CircuitOpenError(upstream)

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
            reraise=True,
        ):
            with attempt:
                try:
                    result = await asyncio.wait_for(fn(*args, **kwargs), timeout=timeout)
                except TimeoutError as e:
                    llm_errors.labels(provider=upstream, model="", reason="timeout").inc()
                    raise UpstreamError(upstream, "timeout") from e
                except UpstreamError:
                    raise
                except Exception as e:
                    reason = type(e).__name__
                    llm_errors.labels(provider=upstream, model="", reason=reason).inc()
                    raise UpstreamError(upstream, f"{reason}: {e}") from e
                breaker.record_success(upstream)
                return result
    except RetryError as e:  # pragma: no cover — tenacity reraise=True usually re-throws inner
        breaker.record_failure(upstream)
        raise UpstreamError(upstream, "retry exhausted") from e
    except UpstreamError:
        breaker.record_failure(upstream)
        raise

    raise UpstreamError(upstream, "unreachable")  # pragma: no cover


async def with_fallback(
    chain: list[str],
    *,
    upstream: str,
    invoke: Callable[[str], Awaitable[T]],
    metrics: TurnMetrics | None = None,
    stage: str | None = None,
    timeout_s: float | None = None,
) -> T:
    """Try each `provider:model` entry in `chain`; return first success.

    On every failure we record a fallback event on `metrics` (if provided) and
    move to the next entry. Raises :class:`AllFallbacksFailedError` if every
    entry fails.
    """
    attempts: list[str] = []
    last_exc: Exception | None = None
    for entry in chain:
        attempts.append(entry)
        try:
            return await call_with_retry(invoke, entry, upstream=upstream, timeout_s=timeout_s)
        except (UpstreamError, Exception) as e:
            last_exc = e
            _log.warning(
                "fallback_hop",
                upstream=upstream,
                attempted=entry,
                error=str(e),
                stage=stage,
            )
            if metrics is not None and stage is not None:
                metrics.record_fallback(stage=stage, reason=str(e), attempted=entry)
            continue
    err = AllFallbacksFailedError(upstream, attempts)
    err.__cause__ = last_exc
    raise err


def resilient(
    *,
    upstream: str,
    timeout_s: float | None = None,
    max_attempts: int | None = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator wrapping a single-upstream async call in retry + timeout + breaker."""

    def deco(fn: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await call_with_retry(
                fn,
                *args,
                upstream=upstream,
                timeout_s=timeout_s,
                max_attempts=max_attempts,
                **kwargs,
            )

        return wrapper

    return deco
