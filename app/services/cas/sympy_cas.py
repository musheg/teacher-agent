"""Thin SymPy wrapper exposed both as a service and as Pydantic AI tools."""

from __future__ import annotations

from typing import Any

import sympy as sp
from pydantic import BaseModel, Field
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from app.core.exceptions import TeacherAgentsError
from app.core.logging import get_logger

_log = get_logger("cas")
_TRANSFORMS = (*standard_transformations, implicit_multiplication_application)


class CASError(TeacherAgentsError):
    """Raised when a CAS operation cannot complete."""


class CASResult(BaseModel):
    """Structured CAS output."""

    success: bool
    result: str | None = None
    latex: str | None = None
    steps: list[str] = Field(default_factory=list)
    detail: str | None = None


def _parse(expr: str) -> sp.Expr:
    try:
        return parse_expr(
            expr.replace("^", "**"),
            transformations=_TRANSFORMS,
            evaluate=False,
        )
    except (SyntaxError, TypeError, ValueError) as e:
        raise CASError(f"could not parse {expr!r}: {e}") from e


class SymPyCAS:
    """Symbolic math helpers."""

    def simplify(self, expression: str) -> CASResult:
        try:
            e = _parse(expression)
            r = sp.simplify(e)
            return CASResult(success=True, result=str(r), latex=sp.latex(r))
        except CASError as e:
            return CASResult(success=False, detail=str(e))

    def factor(self, expression: str) -> CASResult:
        try:
            e = _parse(expression)
            r = sp.factor(e)
            return CASResult(success=True, result=str(r), latex=sp.latex(r))
        except CASError as e:
            return CASResult(success=False, detail=str(e))

    def expand(self, expression: str) -> CASResult:
        try:
            e = _parse(expression)
            r = sp.expand(e)
            return CASResult(success=True, result=str(r), latex=sp.latex(r))
        except CASError as e:
            return CASResult(success=False, detail=str(e))

    def evaluate(self, expression: str, *, subs: dict[str, float] | None = None) -> CASResult:
        try:
            e = _parse(expression)
            if subs:
                e = e.subs({sp.Symbol(k): v for k, v in subs.items()})
            r = sp.N(e)
            return CASResult(success=True, result=str(r), latex=sp.latex(r))
        except CASError as e:
            return CASResult(success=False, detail=str(e))

    def solve(self, equation: str, variable: str | None = None) -> CASResult:
        """Solve an equation (LHS=RHS or expr) for `variable`."""
        try:
            lhs_str, _, rhs_str = equation.partition("=")
            if rhs_str == "":
                expr = _parse(lhs_str)
                eq = sp.Eq(expr, 0)
            else:
                eq = sp.Eq(_parse(lhs_str), _parse(rhs_str))
            free = list(eq.free_symbols)
            if not free:
                return CASResult(success=False, detail="no variables to solve for")
            sym = sp.Symbol(variable) if variable else free[0]
            sols = sp.solve(eq, sym, dict=False)
            text = ", ".join(f"{sym} = {s}" for s in sols) if sols else "no solution"
            return CASResult(
                success=True,
                result=text,
                latex=sp.latex(sols),
                steps=[f"Equation: {sp.latex(eq)}", f"Solve for {sym}"],
            )
        except CASError as e:
            return CASResult(success=False, detail=str(e))

    def verify_equivalence(self, expr_a: str, expr_b: str) -> CASResult:
        """Check whether two expressions are mathematically equivalent."""
        try:
            a = _parse(expr_a)
            b = _parse(expr_b)
            equal = bool(sp.simplify(a - b) == 0)
            return CASResult(success=True, result="equivalent" if equal else "different")
        except CASError as e:
            return CASResult(success=False, detail=str(e))

    def step_by_step(self, problem: str) -> CASResult:
        """Generate a minimal step-by-step explanation.

        For now we cover three common cases: simplify, solve (equation), eval.
        """
        try:
            if "=" in problem:
                eq = self.solve(problem)
                return CASResult(
                    success=eq.success,
                    result=eq.result,
                    latex=eq.latex,
                    steps=[
                        "Parse the equation.",
                        "Move all terms to one side.",
                        "Solve symbolically for the unknown.",
                        f"Answer: {eq.result}",
                    ],
                )
            e = _parse(problem)
            simplified = sp.simplify(e)
            steps = ["Parse the expression."]
            expanded = sp.expand(e)
            if expanded != e:
                steps.append(f"Expand: {sp.simplify(expanded)}")
            if simplified != e:
                steps.append(f"Simplify: {simplified}")
            steps.append(f"Result: {simplified}")
            return CASResult(
                success=True,
                result=str(simplified),
                latex=sp.latex(simplified),
                steps=steps,
            )
        except CASError as e:
            return CASResult(success=False, detail=str(e))

    def as_tool_dict(self) -> dict[str, Any]:
        """Return a dict of named callables for registering as agent tools."""
        return {
            "simplify": self.simplify,
            "factor": self.factor,
            "expand": self.expand,
            "evaluate": self.evaluate,
            "solve": self.solve,
            "verify_equivalence": self.verify_equivalence,
            "step_by_step": self.step_by_step,
        }


cas = SymPyCAS()
"""Shared default instance — SymPy is thread-safe & has no state."""
