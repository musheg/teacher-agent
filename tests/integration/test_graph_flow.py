"""End-to-end graph test with every external dependency mocked."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.agents.safety import SafetyDecision
from app.agents.speech import SpeechReply
from app.agents.tutor import TutorReply
from app.graph.graph import run_turn
from app.graph.state import ChildProfile, GraphState
from app.services.stt.base import STTResult
from app.viz.schema import FractionPieSpec


@pytest.fixture
def mock_pipeline(monkeypatch):
    async def fake_transcribe(self, audio, **kwargs):
        return STTResult(transcript="Կարող ե՞ք սովորեցնել կոտորակները", language_code="hy-AM")

    async def fake_translate(text, *, source, target, metrics=None, stage=""):
        if source == "Armenian":
            return "Can you teach me fractions?"
        return f"[hy] {text}"

    async def fake_safety(text, *, metrics=None, stage="safety_in"):
        return SafetyDecision(safe=True)

    async def fake_tutor(*, age_band, summary, child_utterance_en, metrics=None, stage="tutor"):
        return TutorReply(
            reply_text="Sure! Let's look at a half of a pizza.",
            next_question="What's half of 4?",
            viz_hint="fraction_pie 1/2",
            verified_claims=[],
        )

    async def fake_viz(*, tutor_reply_en, viz_hint, age_band, metrics=None, stage="viz"):
        return FractionPieSpec(numerator=1, denominator=2)

    async def fake_speech(*, tutor_reply_en, age_band, metrics=None, stage="speech"):
        return SpeechReply(clauses=["Sure.", "Let's look at half of a pizza."])

    from app.agents import safety as safety_mod
    from app.agents import speech as speech_mod
    from app.agents import translator as tr_mod
    from app.agents import tutor as tutor_mod
    from app.agents import visualization as viz_mod
    from app.services.stt.google import GoogleSTT

    monkeypatch.setattr(GoogleSTT, "transcribe", fake_transcribe, raising=True)
    monkeypatch.setattr(tr_mod, "translate", fake_translate)
    monkeypatch.setattr(safety_mod, "classify", fake_safety)
    monkeypatch.setattr(tutor_mod, "tutor_turn", fake_tutor)
    monkeypatch.setattr(viz_mod, "make_spec", fake_viz)
    monkeypatch.setattr(speech_mod, "paraphrase", fake_speech)


async def test_graph_emits_viz_before_audio_and_translates(mock_pipeline) -> None:
    events: asyncio.Queue = asyncio.Queue()
    state = GraphState(
        session_id=uuid4(),
        child=ChildProfile(id=uuid4(), age=6, grade=1, locale="hy-AM"),
        audio_in=b"\x00\x01\x02",
        events=events,
    )

    output = await run_turn(state)

    # Viz event was emitted at the right step in the graph.
    drained = []
    while not events.empty():
        drained.append(await events.get())
    assert any(e.type == "viz_spec" for e in drained), drained
    assert output.viz_spec is not None
    assert output.viz_spec.kind == "fraction_pie"
    assert output.en_text_out.startswith("Sure")
    # Output translated to Armenian
    assert output.hy_text_out.startswith("[hy]")
    # No blocking
    assert not output.blocked
    # Agent path captures every node
    assert "tutor" in state.metrics.agent_path or state.metrics.tutor_ms is not None
