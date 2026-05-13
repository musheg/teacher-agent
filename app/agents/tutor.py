"""Tutor agent — Socratic explainer with Solver tools registered."""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.agents.base import run_with_fallback
from app.agents.prompt_loader import load_prompt
from app.core.metrics import TurnMetrics
from app.services.cas import cas
from app.settings import get_settings


class TutorReply(BaseModel):
    reply_text: str
    next_question: str | None = None
    viz_hint: str | None = None
    verified_claims: list[str] = Field(default_factory=list)


def _build_agent(model_name: str) -> Agent[None, TutorReply]:
    agent = Agent(
        model=model_name,
        output_type=TutorReply,
        system_prompt=load_prompt("tutor"),
        defer_model_check=True,
        name="tutor",
    )

    @agent.tool_plain
    def solver_verify(expression: str, expected_answer: str) -> str:
        """Verify that `expression` simplifies/evaluates to `expected_answer`."""
        return cas.verify_equivalence(expression, expected_answer).model_dump_json()

    @agent.tool_plain
    def solver_simplify(expression: str) -> str:
        """Simplify an algebraic/arithmetic expression."""
        return cas.simplify(expression).model_dump_json()

    @agent.tool_plain
    def solver_solve(equation: str, variable: str | None = None) -> str:
        """Solve an equation for a variable."""
        return cas.solve(equation, variable).model_dump_json()

    return agent


class TutorPostValidationError(ValueError):
    """Raised when the Tutor produced unverified math claims."""


async def tutor_turn(
    *,
    age_band: str,
    summary: str,
    child_utterance_en: str,
    metrics: TurnMetrics | None = None,
    stage: str = "tutor",
) -> TutorReply:
    """Run one tutor turn given the child's last English utterance."""
    settings = get_settings()
    user_msg = (
        f"Age band: {age_band}\n"
        f"Prior conversation summary: {summary or '(none)'}\n\n"
        f"Child said: {child_utterance_en}\n\n"
        "Respond in English following the JSON schema."
    )

    async def _invoke(agent: Agent[None, TutorReply]) -> TutorReply:
        result = await agent.run(user_msg)
        return result.output

    reply = await run_with_fallback(
        settings.tutor_model,
        agent_factory=_build_agent,
        invoke=_invoke,
        metrics=metrics,
        stage=stage,
        agent_name="tutor",
    )

    # Lightweight post-hoc heuristic: if the reply asserts a numeric equality
    # like "2 + 3 = 5" but no `verified_claims`, log a warning. The agent
    # already had access to solver_* tools; verification is best-effort here.
    if "=" in reply.reply_text and not reply.verified_claims:
        from app.core.logging import get_logger

        get_logger("tutor").warning(
            "tutor_unverified_claim",
            reply_preview=reply.reply_text[:120],
        )

    return reply
