"""Conversation summarizer used by the Redis context manager."""

from __future__ import annotations

from pydantic_ai import Agent

from app.agents.base import run_with_fallback
from app.agents.prompt_loader import load_prompt
from app.services.context import ContextTurn
from app.settings import get_settings


def _build_agent(model_name: str) -> Agent[None, str]:
    return Agent(
        model=model_name,
        output_type=str,
        system_prompt=load_prompt("summarizer"),
        defer_model_check=True,
        name="summarizer",
    )


async def summarize(*, existing_summary: str, turns: list[ContextTurn]) -> str:
    rendered = "\n".join(f"- {t.role}: {t.text}" for t in turns)
    user = (
        f"Existing summary:\n{existing_summary or '(none)'}\n\n"
        f"New turns to integrate:\n{rendered}\n\n"
        "Return the updated compact summary."
    )

    async def _invoke(agent: Agent[None, str]) -> str:
        result = await agent.run(user)
        return result.output.strip()

    return await run_with_fallback(
        get_settings().summarizer_model,
        agent_factory=_build_agent,
        invoke=_invoke,
        agent_name="summarizer",
    )
