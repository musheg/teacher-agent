"""TurnMetrics model, stage timers, and Prometheus instruments."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram
from pydantic import BaseModel, Field

from app.core.logging import get_logger

_log = get_logger("metrics")

# Dedicated registry so tests can use a fresh one if needed.
REGISTRY = CollectorRegistry()

agent_latency = Histogram(
    "agent_latency_ms",
    "Per-agent latency in milliseconds",
    labelnames=("agent", "model"),
    buckets=(50, 100, 250, 500, 1000, 2000, 4000, 8000, 16000, 32000),
    registry=REGISTRY,
)

llm_errors = Counter(
    "llm_errors_total",
    "Count of LLM upstream errors",
    labelnames=("provider", "model", "reason"),
    registry=REGISTRY,
)

tts_first_byte = Histogram(
    "tts_first_byte_ms",
    "TTS first audio chunk latency in milliseconds",
    labelnames=("provider",),
    buckets=(50, 100, 200, 350, 500, 750, 1000, 2000, 5000),
    registry=REGISTRY,
)

stt_latency = Histogram(
    "stt_latency_ms",
    "STT round-trip latency in milliseconds",
    labelnames=("provider", "model"),
    buckets=(100, 250, 500, 1000, 2000, 5000, 10000),
    registry=REGISTRY,
)

bkt_updates = Counter(
    "bkt_updates_total",
    "Number of BKT posterior updates applied",
    registry=REGISTRY,
)

active_ws_connections = Gauge(
    "ws_active_connections",
    "Number of currently open WebSocket sessions",
    registry=REGISTRY,
)

graph_turns = Counter(
    "graph_turns_total",
    "Number of completed graph turns",
    labelnames=("outcome",),
    registry=REGISTRY,
)


class FallbackEvent(BaseModel):
    """Records a single fallback hop."""

    stage: str
    reason: str
    attempted: str | None = None


class TurnMetrics(BaseModel):
    """Per-turn latency + token + cost breakdown persisted on `Turn`."""

    stt_ms: int | None = None
    safety_in_ms: int | None = None
    translate_in_ms: int | None = None
    curriculum_ms: int | None = None
    tutor_ms: int | None = None
    solver_ms: int | None = None
    assessment_ms: int | None = None
    viz_ms: int | None = None
    speech_ms: int | None = None
    translate_out_ms: int | None = None
    safety_out_ms: int | None = None
    tts_first_byte_ms: int | None = None
    tts_total_ms: int | None = None
    e2e_ms: int | None = None

    tokens_in_total: int = 0
    tokens_out_total: int = 0
    cost_usd_est: float = 0.0

    fallbacks: list[FallbackEvent] = Field(default_factory=list)
    agent_path: list[str] = Field(default_factory=list)

    def record_fallback(self, stage: str, reason: str, attempted: str | None = None) -> None:
        self.fallbacks.append(FallbackEvent(stage=stage, reason=reason, attempted=attempted))

    def add_tokens(self, in_: int, out: int) -> None:
        self.tokens_in_total += in_
        self.tokens_out_total += out


@contextmanager
def stage_timer(metrics: TurnMetrics, field: str, *, agent: str | None = None) -> Iterator[None]:
    """Time a graph stage; write `*_ms` field on TurnMetrics and emit a log/metric.

    `field` is one of the `*_ms` attribute names on TurnMetrics.
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        if hasattr(metrics, field):
            setattr(metrics, field, elapsed_ms)
        if agent:
            metrics.agent_path.append(agent)
            agent_latency.labels(agent=agent, model="").observe(elapsed_ms)
        _log.info(
            "stage_finished",
            stage=field,
            agent=agent,
            duration_ms=elapsed_ms,
        )
