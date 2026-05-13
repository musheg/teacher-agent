"""Speech agent — rewrite Tutor reply into TTS-friendly clauses."""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.agents.base import run_with_fallback
from app.agents.prompt_loader import load_prompt
from app.core.metrics import TurnMetrics
from app.settings import get_settings


class SpeechReply(BaseModel):
    clauses: list[str] = Field(default_factory=list)


def _build_agent(model_name: str) -> Agent[None, SpeechReply]:
    return Agent(
        model=model_name,
        output_type=SpeechReply,
        system_prompt=load_prompt("speech"),
        defer_model_check=True,
        name="speech",
    )


async def paraphrase(
    *,
    tutor_reply_en: str,
    age_band: str,
    metrics: TurnMetrics | None = None,
    stage: str = "speech",
) -> SpeechReply:
    user = (
        f"Age band: {age_band}\n"
        f"Tutor reply (English):\n{tutor_reply_en}\n\n"
        "Rewrite as JSON SpeechReply with a list of clauses."
    )

    async def _invoke(agent: Agent[None, SpeechReply]) -> SpeechReply:
        result = await agent.run(user)
        return result.output

    return await run_with_fallback(
        get_settings().speech_model,
        agent_factory=_build_agent,
        invoke=_invoke,
        metrics=metrics,
        stage=stage,
        agent_name="speech",
    )
