"""Solver agent — drives SymPy via tools."""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from app.agents.base import model_settings, run_with_fallback
from app.agents.prompt_loader import load_prompt
from app.core.metrics import TurnMetrics
from app.services.cas import cas
from app.settings import get_settings


class SolverResult(BaseModel):
    success: bool
    answer: str | None = None
    latex: str | None = None
    steps: list[str] = Field(default_factory=list)
    verified: bool = False
    notes: str | None = None


def _build_agent(model_name: str) -> Agent[None, SolverResult]:
    agent = Agent(
        model=model_name,
        output_type=SolverResult,
        system_prompt=load_prompt("solver"),
        model_settings=model_settings(reasoning_effort="high"),
        defer_model_check=True,
        name="solver",
    )

    @agent.tool_plain
    def sympy_simplify(expression: str) -> str:
        """Simplify a SymPy-compatible expression."""
        r = cas.simplify(expression)
        return r.model_dump_json()

    @agent.tool_plain
    def sympy_factor(expression: str) -> str:
        """Factor a polynomial expression."""
        return cas.factor(expression).model_dump_json()

    @agent.tool_plain
    def sympy_expand(expression: str) -> str:
        """Expand an expression."""
        return cas.expand(expression).model_dump_json()

    @agent.tool_plain
    def sympy_evaluate(expression: str, substitutions: dict[str, float] | None = None) -> str:
        """Numerically evaluate; substitutions like {'x': 2.0}."""
        return cas.evaluate(expression, subs=substitutions).model_dump_json()

    @agent.tool_plain
    def sympy_solve(equation: str, variable: str | None = None) -> str:
        """Solve an equation like 'x + 2 = 5'."""
        return cas.solve(equation, variable).model_dump_json()

    @agent.tool_plain
    def sympy_verify_equivalence(a: str, b: str) -> str:
        """Check if two expressions are mathematically equivalent."""
        return cas.verify_equivalence(a, b).model_dump_json()

    @agent.tool
    def sympy_step_by_step(_ctx: RunContext[None], problem: str) -> str:
        """Produce a step-by-step solution skeleton."""
        return cas.step_by_step(problem).model_dump_json()

    return agent


async def solve(
    problem: str,
    *,
    metrics: TurnMetrics | None = None,
    stage: str = "solver",
) -> SolverResult:
    async def _invoke(agent: Agent[None, SolverResult]) -> SolverResult:
        result = await agent.run(problem)
        return result.output

    return await run_with_fallback(
        get_settings().solver_model,
        agent_factory=_build_agent,
        invoke=_invoke,
        metrics=metrics,
        stage=stage,
        agent_name="solver",
    )
