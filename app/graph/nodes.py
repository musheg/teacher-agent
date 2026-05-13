"""Pydantic-graph nodes wrapping each agent / service call."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_graph import BaseNode, End, GraphRunContext

from app.agents import safety, speech, translator, tutor, visualization
from app.core.exceptions import SafetyBlockError, UpstreamError
from app.core.logging import get_logger
from app.core.metrics import stage_timer
from app.graph.state import GraphEvent, GraphState, TurnOutput
from app.services.stt import get_stt_provider

_log = get_logger("graph")


@dataclass
class STTNode(BaseNode[GraphState, None, TurnOutput]):
    """Convert audio_in (Armenian) to text."""

    async def run(self, ctx: GraphRunContext[GraphState]) -> SafetyInNode | EndNode:
        state = ctx.state
        if state.audio_in is None:
            _log.warning("stt_skipped_no_audio")
            return EndNode(output=state.output)
        with stage_timer(state.metrics, "stt_ms", agent="stt"):
            try:
                stt = get_stt_provider()
                result = await stt.transcribe(state.audio_in)
                state.output.hy_text_in = result.transcript
            except UpstreamError as e:
                _log.warning("stt_failed", error=str(e))
                state.metrics.record_fallback(stage="stt", reason=str(e))
                state.output.blocked = True
                state.output.block_reason = "stt_unavailable"
                return EndNode(output=state.output)
        return SafetyInNode()


@dataclass
class SafetyInNode(BaseNode[GraphState, None, TurnOutput]):
    async def run(self, ctx: GraphRunContext[GraphState]) -> TranslatorInNode | EndNode:
        state = ctx.state
        with stage_timer(state.metrics, "safety_in_ms", agent="safety_in"):
            try:
                decision = await safety.classify(state.output.hy_text_in, metrics=state.metrics)
                if not decision.safe:
                    raise SafetyBlockError("input unsafe", decision.categories)
            except SafetyBlockError as e:
                state.output.blocked = True
                state.output.block_reason = f"unsafe_input:{','.join(e.categories)}"
                return EndNode(output=state.output)
            except Exception as e:
                _log.warning("safety_in_unavailable", error=str(e))
                state.metrics.record_fallback(stage="safety_in", reason=str(e))
        return TranslatorInNode()


@dataclass
class TranslatorInNode(BaseNode[GraphState, None, TurnOutput]):
    async def run(self, ctx: GraphRunContext[GraphState]) -> TutorNode | EndNode:
        state = ctx.state
        with stage_timer(state.metrics, "translate_in_ms", agent="translator_in"):
            try:
                en = await translator.translate(
                    state.output.hy_text_in,
                    source="Armenian",
                    target="English",
                    metrics=state.metrics,
                    stage="translate_in",
                )
                state.output.en_text_in = en
            except Exception as e:
                _log.warning("translate_in_failed", error=str(e))
                state.metrics.record_fallback(stage="translate_in", reason=str(e))
                state.output.en_text_in = state.output.hy_text_in
        return TutorNode()


@dataclass
class TutorNode(BaseNode[GraphState, None, TurnOutput]):
    async def run(self, ctx: GraphRunContext[GraphState]) -> VizNode | EndNode:
        state = ctx.state
        viz_hint: str | None = None
        with stage_timer(state.metrics, "tutor_ms", agent="tutor"):
            try:
                reply = await tutor.tutor_turn(
                    age_band=state.child.age_band,
                    summary=state.summary,
                    child_utterance_en=state.output.en_text_in,
                    metrics=state.metrics,
                )
                state.output.en_text_out = reply.reply_text
                viz_hint = reply.viz_hint
            except Exception as e:
                _log.warning("tutor_failed", error=str(e))
                state.metrics.record_fallback(stage="tutor", reason=str(e))
                state.output.en_text_out = (
                    "I'm having trouble thinking right now. Could you say that again in a moment?"
                )
        return VizNode(viz_hint=viz_hint)


@dataclass
class VizNode(BaseNode[GraphState, None, TurnOutput]):
    """Generate a VisualizationSpec and emit it immediately to the client."""

    viz_hint: str | None = None

    async def run(self, ctx: GraphRunContext[GraphState]) -> SpeechNode:
        state = ctx.state
        with stage_timer(state.metrics, "viz_ms", agent="visualization"):
            try:
                spec = await visualization.make_spec(
                    tutor_reply_en=state.output.en_text_out,
                    viz_hint=self.viz_hint,
                    age_band=state.child.age_band,
                    metrics=state.metrics,
                )
                state.output.viz_spec = spec
                # Emit BEFORE audio — child sees the picture as they hear the answer.
                await state.emit(
                    GraphEvent(type="viz_spec", payload={"spec": spec.model_dump(mode="json")})
                )
            except Exception as e:
                _log.warning("viz_failed", error=str(e))
                state.metrics.record_fallback(stage="viz", reason=str(e))
        return SpeechNode()


@dataclass
class SpeechNode(BaseNode[GraphState, None, TurnOutput]):
    """Paraphrase the tutor reply into TTS-friendly clauses (English)."""

    async def run(self, ctx: GraphRunContext[GraphState]) -> TranslatorOutNode:
        state = ctx.state
        with stage_timer(state.metrics, "speech_ms", agent="speech"):
            try:
                paraphrased = await speech.paraphrase(
                    tutor_reply_en=state.output.en_text_out,
                    age_band=state.child.age_band,
                    metrics=state.metrics,
                )
                # Keep English clauses on state; translation happens next.
                state.output.clauses_hy = paraphrased.clauses or [state.output.en_text_out]
            except Exception as e:
                _log.warning("speech_failed", error=str(e))
                state.metrics.record_fallback(stage="speech", reason=str(e))
                state.output.clauses_hy = [state.output.en_text_out]
        return TranslatorOutNode()


@dataclass
class TranslatorOutNode(BaseNode[GraphState, None, TurnOutput]):
    """Translate each clause back to Armenian for TTS."""

    async def run(self, ctx: GraphRunContext[GraphState]) -> SafetyOutNode:
        state = ctx.state
        with stage_timer(state.metrics, "translate_out_ms", agent="translator_out"):
            translated: list[str] = []
            for clause in state.output.clauses_hy:
                try:
                    hy = await translator.translate(
                        clause,
                        source="English",
                        target="Armenian",
                        metrics=state.metrics,
                        stage="translate_out",
                    )
                except Exception as e:
                    _log.warning("translate_out_failed", error=str(e), clause=clause[:40])
                    state.metrics.record_fallback(stage="translate_out", reason=str(e))
                    hy = clause
                translated.append(hy)
            state.output.clauses_hy = translated
            state.output.hy_text_out = " ".join(translated)
        return SafetyOutNode()


@dataclass
class SafetyOutNode(BaseNode[GraphState, None, TurnOutput]):
    async def run(self, ctx: GraphRunContext[GraphState]) -> EndNode:
        state = ctx.state
        with stage_timer(state.metrics, "safety_out_ms", agent="safety_out"):
            try:
                decision = await safety.classify(
                    state.output.hy_text_out, metrics=state.metrics, stage="safety_out"
                )
                if not decision.safe:
                    state.output.blocked = True
                    state.output.block_reason = "unsafe_output"
                    state.output.clauses_hy = ["Ներողություն, փորձենք այլ կերպ բացատրել։"]
                    state.output.hy_text_out = state.output.clauses_hy[0]
            except Exception as e:
                _log.warning("safety_out_unavailable", error=str(e))
                state.metrics.record_fallback(stage="safety_out", reason=str(e))
        return EndNode(output=state.output)


@dataclass
class EndNode(BaseNode[GraphState, None, TurnOutput]):
    output: TurnOutput

    async def run(self, ctx: GraphRunContext[GraphState]) -> End[TurnOutput]:
        return End(self.output)
