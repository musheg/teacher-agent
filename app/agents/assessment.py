"""Assessment agent — quiz generation and grading."""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.agents.base import run_with_fallback
from app.agents.prompt_loader import load_prompt
from app.core.metrics import TurnMetrics
from app.services.cas import cas
from app.settings import get_settings


class QuizItem(BaseModel):
    prompt: str
    choices: list[str] | None = None
    expected_answer: str | None = None
    skill_code: str
    difficulty: int = Field(default=1, ge=1, le=5)


class AssessmentResult(BaseModel):
    mode: str  # "generate" or "grade"
    item: QuizItem | None = None
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    feedback: str | None = None
    correct_answer: str | None = None


def _build_agent(model_name: str) -> Agent[None, AssessmentResult]:
    agent = Agent(
        model=model_name,
        output_type=AssessmentResult,
        system_prompt=load_prompt("assessment"),
        defer_model_check=True,
        name="assessment",
    )

    @agent.tool_plain
    def cas_verify(student_answer: str, expected_answer: str) -> str:
        """Verify equivalence of student vs expected expressions."""
        return cas.verify_equivalence(student_answer, expected_answer).model_dump_json()

    return agent


async def generate_item(
    *,
    skill_code: str,
    difficulty: int,
    age_band: str,
    metrics: TurnMetrics | None = None,
    stage: str = "assessment",
) -> AssessmentResult:
    user = (
        f"Mode: generate\nAge band: {age_band}\n"
        f"Skill: {skill_code}\nDifficulty: {difficulty}\n"
        "Generate one short quiz item with prompt + expected_answer."
    )

    async def _invoke(agent: Agent[None, AssessmentResult]) -> AssessmentResult:
        result = await agent.run(user)
        return result.output

    return await run_with_fallback(
        get_settings().assessment_model,
        agent_factory=_build_agent,
        invoke=_invoke,
        metrics=metrics,
        stage=stage,
        agent_name="assessment.generate",
    )


async def grade_answer(
    *,
    skill_code: str,
    item: QuizItem,
    student_answer: str,
    metrics: TurnMetrics | None = None,
    stage: str = "assessment",
) -> AssessmentResult:
    user = (
        f"Mode: grade\nSkill: {skill_code}\n"
        f"Question: {item.prompt}\n"
        f"Expected answer: {item.expected_answer}\n"
        f"Student answer: {student_answer}\n"
        "Return JSON AssessmentResult with score, feedback, correct_answer."
    )

    async def _invoke(agent: Agent[None, AssessmentResult]) -> AssessmentResult:
        result = await agent.run(user)
        return result.output

    return await run_with_fallback(
        get_settings().assessment_model,
        agent_factory=_build_agent,
        invoke=_invoke,
        metrics=metrics,
        stage=stage,
        agent_name="assessment.grade",
    )
