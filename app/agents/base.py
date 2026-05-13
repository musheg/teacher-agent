"""Helpers shared by every Pydantic AI agent in the system."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from pydantic_ai import Agent
from pydantic_ai.usage import RunUsage

from app.core.exceptions import AllFallbacksFailedError
from app.core.logging import get_logger
from app.core.metrics import TurnMetrics
from app.settings import ModelChain, get_settings

T = TypeVar("T")
_log = get_logger("agents")


def primary_model(chain: ModelChain | list[str]) -> str:
    """Return the first model in the chain (primary)."""
    if not chain:
        raise ValueError("model chain is empty")
    return chain[0]


def fallback_models(chain: ModelChain | list[str]) -> list[str]:
    return list(chain[1:])


def model_settings(*, reasoning_effort: str | None = None) -> dict[str, Any]:
    """Return optional model_settings (e.g. reasoning effort for GPT-5 models)."""
    s: dict[str, Any] = {}
    if reasoning_effort is not None:
        # OpenAI-style key — providers that don't know it just ignore.
        s["openai_reasoning_effort"] = reasoning_effort
    return s


async def run_with_fallback(
    chain: ModelChain | list[str],
    *,
    agent_factory: Callable[[str], Agent[Any, T]],
    invoke: Callable[[Agent[Any, T]], Awaitable[T]],
    metrics: TurnMetrics | None = None,
    stage: str | None = None,
    agent_name: str | None = None,
) -> T:
    """Try each model in `chain`; return first success.

    `agent_factory(model_name)` should build a fresh Agent with that model
    (and the same system prompt, tools, output type).
    `invoke(agent)` calls `await agent.run(...)` and returns the typed output.
    """
    attempts: list[str] = []
    last_exc: Exception | None = None
    for model_name in chain:
        attempts.append(model_name)
        agent = agent_factory(model_name)
        start = time.perf_counter()
        try:
            result = await invoke(agent)
            dur_ms = int((time.perf_counter() - start) * 1000)
            _log.info(
                "agent_run_ok",
                agent=agent_name,
                model=model_name,
                duration_ms=dur_ms,
            )
            return result
        except Exception as e:
            dur_ms = int((time.perf_counter() - start) * 1000)
            last_exc = e
            _log.warning(
                "agent_run_failed",
                agent=agent_name,
                model=model_name,
                duration_ms=dur_ms,
                error=str(e),
            )
            if metrics is not None and stage is not None:
                metrics.record_fallback(stage=stage, reason=str(e), attempted=model_name)
            continue
    err = AllFallbacksFailedError(agent_name or "agent", attempts)
    err.__cause__ = last_exc
    raise err


def accumulate_usage(usage: RunUsage, metrics: TurnMetrics) -> None:
    """Add a `RunUsage` (pydantic_ai) into TurnMetrics counters."""
    if not usage:
        return
    # pydantic_ai RunUsage exposes `input_tokens`, `output_tokens`, `request_tokens`, etc.
    in_t = getattr(usage, "input_tokens", None) or getattr(usage, "request_tokens", 0) or 0
    out_t = getattr(usage, "output_tokens", None) or getattr(usage, "response_tokens", 0) or 0
    metrics.add_tokens(in_t, out_t)


def settings() -> Any:
    return get_settings()
