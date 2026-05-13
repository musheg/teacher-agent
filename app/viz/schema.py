"""Typed VisualizationSpec discriminated union emitted by the Visualization agent."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


# ── Animation primitives ────────────────────────────────────────────
class AnimationFrame(BaseModel):
    """A single frame in a viz timeline; played at offset `t_ms` from TTS start."""

    t_ms: int = Field(ge=0, description="Frame offset in milliseconds from TTS start")
    ops: list[dict] = Field(
        default_factory=list,
        description="Renderer-specific ops, e.g. {'op':'highlight','id':'p1'}",
    )


class _BaseSpec(BaseModel):
    """Common base for every spec kind."""

    title: str | None = None
    caption: str | None = None
    frames: list[AnimationFrame] = Field(
        default_factory=list, description="Optional animation timeline"
    )


# ── number_line ─────────────────────────────────────────────────────
class NumberLineMark(BaseModel):
    value: float
    label: str | None = None
    color: str | None = None


class NumberLineSpec(_BaseSpec):
    kind: Literal["number_line"] = "number_line"
    start: float
    end: float
    step: float = 1.0
    marks: list[NumberLineMark] = Field(default_factory=list)
    highlight_intervals: list[tuple[float, float]] = Field(default_factory=list)


# ── fraction_pie ────────────────────────────────────────────────────
class FractionPieSpec(_BaseSpec):
    kind: Literal["fraction_pie"] = "fraction_pie"
    numerator: int = Field(ge=0)
    denominator: int = Field(gt=0)
    label_numerator: str | None = None
    label_denominator: str | None = None
    color_filled: str | None = None
    color_empty: str | None = None


# ── equation_steps ──────────────────────────────────────────────────
class EquationStep(BaseModel):
    latex: str
    explanation: str | None = None
    highlight: list[str] = Field(default_factory=list, description="Token ids to highlight")


class EquationStepsSpec(_BaseSpec):
    kind: Literal["equation_steps"] = "equation_steps"
    steps: list[EquationStep] = Field(min_length=1)


# ── function_plot ───────────────────────────────────────────────────
class FunctionPlotSpec(_BaseSpec):
    kind: Literal["function_plot"] = "function_plot"
    expression: str = Field(description="SymPy-parseable expression, e.g. 'x**2 + 2*x - 1'")
    variable: str = "x"
    x_min: float = -10.0
    x_max: float = 10.0
    y_min: float | None = None
    y_max: float | None = None
    markers: list[dict] = Field(default_factory=list)


# ── geometry ────────────────────────────────────────────────────────
class GeometryConstruction(BaseModel):
    """JSXGraph-friendly construction step."""

    op: Literal[
        "point",
        "line",
        "segment",
        "circle",
        "polygon",
        "angle",
        "label",
        "triangle",
    ]
    id: str | None = None
    args: list = Field(default_factory=list)
    style: dict = Field(default_factory=dict)


class GeometrySpec(_BaseSpec):
    kind: Literal["geometry"] = "geometry"
    bounds: tuple[float, float, float, float] = (-5.0, 5.0, 5.0, -5.0)
    constructions: list[GeometryConstruction] = Field(min_length=1)


# ── bar_chart ───────────────────────────────────────────────────────
class BarChartSpec(_BaseSpec):
    kind: Literal["bar_chart"] = "bar_chart"
    categories: list[str] = Field(min_length=1)
    values: list[float] = Field(min_length=1)
    y_label: str | None = None
    x_label: str | None = None


# ── animation_timeline (pure timeline; ops drive a generic SVG canvas) ──
class AnimationTimelineSpec(_BaseSpec):
    kind: Literal["animation_timeline"] = "animation_timeline"
    width: int = 600
    height: int = 400
    initial_objects: list[dict] = Field(default_factory=list)
    duration_ms: int = Field(default=4000, ge=0)


VisualizationSpec = Annotated[
    NumberLineSpec
    | FractionPieSpec
    | EquationStepsSpec
    | FunctionPlotSpec
    | GeometrySpec
    | BarChartSpec
    | AnimationTimelineSpec,
    Field(discriminator="kind"),
]
"""Discriminated union of all supported visualization kinds."""
