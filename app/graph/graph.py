"""Pydantic Graph definition + run helper."""

from __future__ import annotations

from pydantic_graph import Graph

from app.graph.nodes import (
    EndNode,
    SafetyInNode,
    SafetyOutNode,
    SpeechNode,
    STTNode,
    TranslatorInNode,
    TranslatorOutNode,
    TutorNode,
    VizNode,
)
from app.graph.state import GraphState, TurnOutput

teacher_graph: Graph[GraphState, None, TurnOutput] = Graph(
    nodes=(
        STTNode,
        SafetyInNode,
        TranslatorInNode,
        TutorNode,
        VizNode,
        SpeechNode,
        TranslatorOutNode,
        SafetyOutNode,
        EndNode,
    ),
    state_type=GraphState,
)


async def run_turn(state: GraphState) -> TurnOutput:
    """Run one full turn through the graph."""
    result = await teacher_graph.run(STTNode(), state=state)
    return result.output
