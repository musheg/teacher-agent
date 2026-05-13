"""Visualization agent — emits typed VisualizationSpec JSON."""

from __future__ import annotations

from pydantic import TypeAdapter
from pydantic_ai import Agent

from app.agents.base import run_with_fallback
from app.agents.prompt_loader import load_prompt
from app.core.metrics import TurnMetrics
from app.settings import get_settings
from app.viz.schema import VisualizationSpec

_adapter: TypeAdapter[VisualizationSpec] = TypeAdapter(VisualizationSpec)


def _build_agent(model_name: str) -> Agent[None, VisualizationSpec]:
    return Agent(
        model=model_name,
        output_type=VisualizationSpec,
        system_prompt=load_prompt("visualization"),
        defer_model_check=True,
        name="visualization",
    )


async def make_spec(
    *,
    tutor_reply_en: str,
    viz_hint: str | None,
    age_band: str,
    metrics: TurnMetrics | None = None,
    stage: str = "viz",
) -> VisualizationSpec:
    user = (
        f"Age band: {age_band}\n"
        f"Tutor reply:\n{tutor_reply_en}\n\n"
        f"Visualization hint: {viz_hint or '(none provided)'}\n\n"
        "Produce one VisualizationSpec JSON now."
    )

    async def _invoke(agent: Agent[None, VisualizationSpec]) -> VisualizationSpec:
        result = await agent.run(user)
        return result.output

    return await run_with_fallback(
        get_settings().visualization_model,
        agent_factory=_build_agent,
        invoke=_invoke,
        metrics=metrics,
        stage=stage,
        agent_name="visualization",
    )


def validate_spec(payload: dict) -> VisualizationSpec:
    """Validate a raw dict against VisualizationSpec — useful for tests."""
    return _adapter.validate_python(payload)
