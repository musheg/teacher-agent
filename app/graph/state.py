"""Graph state, events, and the per-turn output container."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.metrics import TurnMetrics
from app.viz.schema import VisualizationSpec


def age_band_from_age(age: int) -> str:
    if age <= 7:
        return "5-7"
    if age <= 11:
        return "8-11"
    if age <= 15:
        return "12-15"
    return "16-18"


@dataclass
class ChildProfile:
    id: UUID
    age: int
    grade: int | None
    locale: str = "hy-AM"

    @property
    def age_band(self) -> str:
        return age_band_from_age(self.age)


@dataclass
class GraphEvent:
    """An event emitted by the graph to the orchestrator (WebSocket)."""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnOutput:
    """Aggregated turn result returned by the graph."""

    hy_text_in: str = ""
    en_text_in: str = ""
    en_text_out: str = ""
    hy_text_out: str = ""
    viz_spec: VisualizationSpec | None = None
    clauses_hy: list[str] = field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None


@dataclass
class GraphState:
    """Mutable state passed between graph nodes."""

    session_id: UUID
    child: ChildProfile
    audio_in: bytes | None = None
    summary: str = ""
    output: TurnOutput = field(default_factory=TurnOutput)
    metrics: TurnMetrics = field(default_factory=TurnMetrics)
    events: asyncio.Queue[GraphEvent] | None = None

    async def emit(self, event: GraphEvent) -> None:
        if self.events is not None:
            await self.events.put(event)
