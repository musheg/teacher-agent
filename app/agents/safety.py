"""Safety In/Out agent combining OpenAI Moderation API and an LLM classifier."""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.agents.base import primary_model, run_with_fallback
from app.agents.prompt_loader import load_prompt
from app.core.logging import get_logger
from app.core.metrics import TurnMetrics
from app.core.resilience import resilient
from app.settings import get_settings

_log = get_logger("safety")


class SafetyDecision(BaseModel):
    safe: bool
    categories: list[str] = Field(default_factory=list)
    rationale: str | None = None


@resilient(upstream="openai_moderation")
async def _moderation_check(text: str) -> SafetyDecision | None:
    """Run OpenAI Moderation API. Returns a clear decision when confident."""
    from openai import AsyncOpenAI

    settings = get_settings()
    if not settings.openai_api_key:
        return None
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.moderations.create(model=settings.moderation_model, input=text)
    res = resp.results[0]
    if res.flagged:
        flagged_categories = [cat for cat, v in res.categories.model_dump().items() if bool(v)]
        return SafetyDecision(
            safe=False,
            categories=flagged_categories,
            rationale="flagged by openai moderation",
        )
    # Confidence threshold for the "safe" fast-path.
    scores = res.category_scores.model_dump()
    if max(scores.values()) < 0.2:
        return SafetyDecision(safe=True)
    return None  # ambiguous — let the classifier decide.


def _build_agent(model_name: str) -> Agent[None, SafetyDecision]:
    return Agent(
        model=model_name,
        output_type=SafetyDecision,
        system_prompt=load_prompt("safety"),
        defer_model_check=True,
        name="safety",
    )


async def classify(
    text: str,
    *,
    metrics: TurnMetrics | None = None,
    stage: str = "safety_in",
) -> SafetyDecision:
    if not text.strip():
        return SafetyDecision(safe=True)

    try:
        fast = await _moderation_check(text)
        if fast is not None:
            return fast
    except Exception as e:
        _log.warning("moderation_unavailable", error=str(e))

    settings = get_settings()

    async def _invoke(agent: Agent[None, SafetyDecision]) -> SafetyDecision:
        result = await agent.run(text)
        return result.output

    return await run_with_fallback(
        settings.safety_model,
        agent_factory=_build_agent,
        invoke=_invoke,
        metrics=metrics,
        stage=stage,
        agent_name="safety",
    )


def primary() -> str:
    return primary_model(get_settings().safety_model)
