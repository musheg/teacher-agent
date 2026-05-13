"""Curriculum Manager agent — picks the next activity."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.agents.base import run_with_fallback
from app.agents.prompt_loader import load_prompt
from app.core.metrics import TurnMetrics
from app.settings import get_settings


class ActivityType(str, Enum):
    EXPLAIN = "EXPLAIN"
    PRACTICE = "PRACTICE"
    QUIZ = "QUIZ"
    REVIEW = "REVIEW"


class CurriculumDecision(BaseModel):
    activity: ActivityType
    skill_code: str
    difficulty: int = Field(ge=1, le=5)
    rationale: str


def _build_agent(model_name: str) -> Agent[None, CurriculumDecision]:
    return Agent(
        model=model_name,
        output_type=CurriculumDecision,
        system_prompt=load_prompt("curriculum"),
        defer_model_check=True,
        name="curriculum",
    )


async def decide_next(
    *,
    age_band: str,
    summary: str,
    masteries: list[dict],
    due_reviews: list[dict],
    child_utterance_en: str | None = None,
    metrics: TurnMetrics | None = None,
    stage: str = "curriculum",
) -> CurriculumDecision:
    user = (
        f"Age band: {age_band}\n"
        f"Conversation summary: {summary or '(none)'}\n"
        f"Current masteries (skill_code -> p_known): {masteries}\n"
        f"Due reviews: {due_reviews}\n"
        f"Last child utterance: {child_utterance_en or '(none)'}\n\n"
        "Decide what should happen next."
    )

    async def _invoke(agent: Agent[None, CurriculumDecision]) -> CurriculumDecision:
        result = await agent.run(user)
        return result.output

    return await run_with_fallback(
        get_settings().curriculum_model,
        agent_factory=_build_agent,
        invoke=_invoke,
        metrics=metrics,
        stage=stage,
        agent_name="curriculum",
    )
