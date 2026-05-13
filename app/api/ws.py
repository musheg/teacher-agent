"""WebSocket session endpoint that streams the graph turn to the client.

Protocol (JSON text frames) + audio is sent as binary frames:

Client -> Server:
  text: {"type":"start","request_id":"...","language":"hy-AM"}
  binary: <audio bytes for current utterance>
  text: {"type":"end_utterance","request_id":"..."}    # finalize and run graph
  text: {"type":"close"}                               # close session

Server -> Client:
  text: {"type":"viz_spec","seq":0,"payload":{...VisualizationSpec...}}
  text: {"type":"audio_meta","seq":k,"mime":"audio/mpeg"}
  binary: <audio chunk bytes for clause k>
  text: {"type":"audio_end","seq":k}
  text: {"type":"turn_complete","metrics":{...},"hy_text_in":"...","hy_text_out":"..."}
  text: {"type":"error","detail":"..."}
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from ulid import ULID

from app.core.context_vars import set_request_context
from app.core.exceptions import AuthError
from app.core.logging import get_logger
from app.core.metrics import TurnMetrics, active_ws_connections, graph_turns
from app.core.security import TokenKind, decode_token
from app.db.models import Child, Turn
from app.db.models import Session as DbSession
from app.db.session import get_sessionmaker
from app.graph.graph import run_turn
from app.graph.state import ChildProfile, GraphEvent, GraphState
from app.services.context import ContextManager, ContextTurn
from app.services.tts import get_tts_provider

router = APIRouter(prefix="/api/ws", tags=["ws"])
_log = get_logger("ws")


async def _authenticate_ws(ws: WebSocket, token: str | None) -> Child:
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="missing token")
        raise AuthError("missing token")
    try:
        payload = decode_token(token, expected_kind=TokenKind.CHILD)
    except AuthError as e:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason=str(e))
        raise
    async with get_sessionmaker()() as session:
        child = await session.get(Child, UUID(payload["sub"]))
        if child is None:
            await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="child not found")
            raise AuthError("child not found")
        return child


async def _create_session_row(child: Child) -> DbSession:
    async with get_sessionmaker()() as session:
        s = DbSession(child_id=child.id, locale=child.locale, started_at=datetime.now(UTC))
        session.add(s)
        await session.commit()
        await session.refresh(s)
        return s


async def _persist_turn(
    *,
    session_id: UUID,
    state: GraphState,
    request_id: str,
    e2e_ms: int,
) -> None:
    async with get_sessionmaker()() as session:
        turn = Turn(
            session_id=session_id,
            hy_text_in=state.output.hy_text_in,
            en_text_in=state.output.en_text_in,
            en_text_out=state.output.en_text_out,
            hy_text_out=state.output.hy_text_out,
            viz_spec=state.output.viz_spec.model_dump(mode="json")
            if state.output.viz_spec
            else None,
            stt_ms=state.metrics.stt_ms,
            safety_in_ms=state.metrics.safety_in_ms,
            translate_in_ms=state.metrics.translate_in_ms,
            curriculum_ms=state.metrics.curriculum_ms,
            tutor_ms=state.metrics.tutor_ms,
            solver_ms=state.metrics.solver_ms,
            assessment_ms=state.metrics.assessment_ms,
            viz_ms=state.metrics.viz_ms,
            speech_ms=state.metrics.speech_ms,
            translate_out_ms=state.metrics.translate_out_ms,
            safety_out_ms=state.metrics.safety_out_ms,
            tts_first_byte_ms=state.metrics.tts_first_byte_ms,
            tts_total_ms=state.metrics.tts_total_ms,
            e2e_ms=e2e_ms,
            tokens_in_total=state.metrics.tokens_in_total,
            tokens_out_total=state.metrics.tokens_out_total,
            cost_usd_est=state.metrics.cost_usd_est,
            fallbacks=[f.model_dump() for f in state.metrics.fallbacks],
            agent_path=list(state.metrics.agent_path),
            request_id=request_id,
        )
        session.add(turn)
        await session.commit()


@router.websocket("/session")
async def session_ws(ws: WebSocket, token: str | None = Query(default=None)) -> None:
    await ws.accept()
    active_ws_connections.inc()
    request_id = str(ULID())
    set_request_context(request_id=request_id)

    try:
        child = await _authenticate_ws(ws, token)
    except AuthError:
        active_ws_connections.dec()
        return

    set_request_context(child_id=child.id, parent_id=child.parent_id, user_role="child")
    db_session = await _create_session_row(child)
    ctx_mgr = ContextManager.from_settings()

    profile = ChildProfile(
        id=child.id,
        age=_calc_age(child.birthdate),
        grade=child.grade,
        locale=child.locale,
    )

    audio_buf: bytearray = bytearray()

    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if "bytes" in msg and msg["bytes"] is not None:
                audio_buf.extend(msg["bytes"])
                continue
            if "text" not in msg or msg["text"] is None:
                continue
            envelope = json.loads(msg["text"])
            etype = envelope.get("type")
            if etype == "start":
                audio_buf.clear()
                _log.info("ws_start", request_id=envelope.get("request_id"))
                continue
            if etype == "close":
                break
            if etype != "end_utterance":
                continue

            req_id = envelope.get("request_id") or str(ULID())
            set_request_context(request_id=req_id)
            audio_bytes = bytes(audio_buf)
            audio_buf.clear()

            summary = await ctx_mgr.get_summary(db_session.id)
            state = GraphState(
                session_id=db_session.id,
                child=profile,
                audio_in=audio_bytes if audio_bytes else None,
                summary=summary,
                metrics=TurnMetrics(),
                events=asyncio.Queue(),
            )

            # Run the graph + drain events concurrently.
            t0 = time.perf_counter()
            drain_task = asyncio.create_task(_drain_events(ws, state.events, req_id))
            try:
                output = await run_turn(state)
            finally:
                # Signal the drainer to stop.
                if state.events is not None:
                    await state.events.put(GraphEvent(type="__done__"))
                await drain_task

            # Stream TTS clauses (if not blocked).
            tts_total_ms = 0
            if not output.blocked and output.clauses_hy:
                tts_start = time.perf_counter()
                provider = get_tts_provider()
                await ws.send_text(json.dumps({"type": "tts_started", "request_id": req_id}))
                for seq, clause in enumerate(output.clauses_hy):
                    await ws.send_text(
                        json.dumps(
                            {
                                "type": "audio_meta",
                                "seq": seq,
                                "mime": provider.audio_mime,
                                "text": clause,
                                "request_id": req_id,
                            }
                        )
                    )
                    try:
                        async for chunk in provider.synthesize(clause, locale=child.locale):
                            await ws.send_bytes(chunk)
                    except Exception as e:
                        _log.warning("tts_failed", error=str(e), seq=seq)
                        state.metrics.record_fallback(stage="tts", reason=str(e))
                    await ws.send_text(
                        json.dumps({"type": "audio_end", "seq": seq, "request_id": req_id})
                    )
                tts_total_ms = int((time.perf_counter() - tts_start) * 1000)
                state.metrics.tts_total_ms = tts_total_ms

            e2e_ms = int((time.perf_counter() - t0) * 1000)
            state.metrics.e2e_ms = e2e_ms

            # Persist turn + update context.
            await _persist_turn(
                session_id=db_session.id, state=state, request_id=req_id, e2e_ms=e2e_ms
            )
            if output.hy_text_in:
                await ctx_mgr.append(
                    db_session.id,
                    ContextTurn(role="child", text=output.hy_text_in),
                )
            if output.hy_text_out:
                await ctx_mgr.append(
                    db_session.id,
                    ContextTurn(role="tutor", text=output.hy_text_out),
                )
            graph_turns.labels(outcome="blocked" if output.blocked else "ok").inc()

            await ws.send_text(
                json.dumps(
                    {
                        "type": "turn_complete",
                        "request_id": req_id,
                        "blocked": output.blocked,
                        "block_reason": output.block_reason,
                        "hy_text_in": output.hy_text_in,
                        "hy_text_out": output.hy_text_out,
                        "metrics": {
                            "e2e_ms": e2e_ms,
                            "tts_total_ms": tts_total_ms,
                            "stt_ms": state.metrics.stt_ms,
                            "tutor_ms": state.metrics.tutor_ms,
                            "tts_first_byte_ms": state.metrics.tts_first_byte_ms,
                            "tokens_in": state.metrics.tokens_in_total,
                            "tokens_out": state.metrics.tokens_out_total,
                            "fallbacks": [f.model_dump() for f in state.metrics.fallbacks],
                            "agent_path": list(state.metrics.agent_path),
                        },
                    }
                )
            )
    except WebSocketDisconnect:
        _log.info("ws_disconnect", session_id=str(db_session.id))
    finally:
        with contextlib.suppress(Exception):
            await ctx_mgr.close()
        async with get_sessionmaker()() as session:
            db_session.ended_at = datetime.now(UTC)
            session.add(db_session)
            await session.commit()
        active_ws_connections.dec()


async def _drain_events(
    ws: WebSocket, queue: asyncio.Queue[GraphEvent] | None, request_id: str
) -> None:
    """Forward graph events to the WS client until a `__done__` sentinel arrives."""
    if queue is None:
        return
    while True:
        try:
            evt = await queue.get()
        except asyncio.CancelledError:
            return
        if evt.type == "__done__":
            return
        await ws.send_text(json.dumps({"type": evt.type, "request_id": request_id, **evt.payload}))


def _calc_age(birthdate) -> int:
    today = datetime.now(UTC).date()
    years = today.year - birthdate.year
    if (today.month, today.day) < (birthdate.month, birthdate.day):
        years -= 1
    return max(0, years)


# Lightweight non-streaming chat endpoint kept for testing / non-WS clients.
@router.post("/chat")
async def chat_oneshot() -> dict:
    return {"detail": "Use the /api/ws/session WebSocket instead."}
