"""Two-track translator: prose-only and math-aware (LaTeX/SymPy preserving)."""

from __future__ import annotations

import re

from pydantic_ai import Agent

from app.agents.base import run_with_fallback
from app.agents.prompt_loader import load_prompt
from app.core.logging import get_logger
from app.core.metrics import TurnMetrics
from app.settings import get_settings

_log = get_logger("translator")

# Math content detection — any of these patterns triggers the math-aware track.
_MATH_DETECT_RE = re.compile(
    r"(\$[^$]+\$)"  # inline LaTeX
    r"|(\\\[[^\]]+\\\])"  # block LaTeX
    r"|([a-zA-Z]\s*=\s*[^,\s]+)"  # variable assignments
    r"|([0-9]+\s*[+\-*/=^][\s0-9]+)"  # numeric expressions
    r"|(\\frac\{)"  # \frac{
    r"|(\\sqrt\{)"  # \sqrt{
)

# Extract math tokens to mask.
_MATH_TOKEN_RE = re.compile(
    r"(\$[^$]+\$"  # inline LaTeX
    r"|\\\[[^\]]+\\\]"  # block LaTeX
    r"|\\frac\{[^{}]+\}\{[^{}]+\}"
    r"|\\sqrt\{[^{}]+\}"
    r"|[a-zA-Z_]\w*\s*=\s*[^\s,;.]+"
    r"|\b\d+\s*[+\-*/=^]\s*\d+(?:\s*[+\-*/=^]\s*\d+)*"
    r"|\d+/\d+)"
)

_PLACEHOLDER_FMT = "〚M{i}〛"


def needs_math_aware(text: str) -> bool:
    return bool(_MATH_DETECT_RE.search(text))


def _mask_math(text: str) -> tuple[str, list[str]]:
    tokens: list[str] = []

    def _sub(match: re.Match[str]) -> str:
        tokens.append(match.group(0))
        return _PLACEHOLDER_FMT.format(i=len(tokens) - 1)

    masked = _MATH_TOKEN_RE.sub(_sub, text)
    return masked, tokens


def _restore_math(text: str, tokens: list[str]) -> str:
    for i, tok in enumerate(tokens):
        text = text.replace(_PLACEHOLDER_FMT.format(i=i), tok)
    return text


def _prose_agent_factory(model_name: str) -> Agent[None, str]:
    return Agent(
        model=model_name,
        output_type=str,
        system_prompt=load_prompt("translator_prose"),
        defer_model_check=True,
        name="translator_prose",
    )


def _math_agent_factory(model_name: str) -> Agent[None, str]:
    return Agent(
        model=model_name,
        output_type=str,
        system_prompt=load_prompt("translator_math"),
        defer_model_check=True,
        name="translator_math",
    )


async def translate_prose(
    text: str,
    *,
    source: str,
    target: str,
    metrics: TurnMetrics | None = None,
    stage: str = "translate",
) -> str:
    """Translate plain prose between languages."""
    if not text.strip():
        return text
    user = f"Translate from {source} to {target}:\n\n{text}"

    async def _invoke(agent: Agent[None, str]) -> str:
        result = await agent.run(user)
        return result.output.strip().strip('"').strip("'")

    return await run_with_fallback(
        get_settings().translator_prose_model,
        agent_factory=_prose_agent_factory,
        invoke=_invoke,
        metrics=metrics,
        stage=stage,
        agent_name="translator_prose",
    )


async def translate_math_aware(
    text: str,
    *,
    source: str,
    target: str,
    metrics: TurnMetrics | None = None,
    stage: str = "translate",
) -> str:
    """Translate text containing math expressions, preserving them byte-identical."""
    if not text.strip():
        return text
    masked, tokens = _mask_math(text)
    if not tokens:
        return await translate_prose(
            text, source=source, target=target, metrics=metrics, stage=stage
        )
    user = (
        f"Translate from {source} to {target}. Keep the placeholders "
        f"〚M0〛, 〚M1〛, ... exactly as-is and in the same order.\n\n{masked}"
    )

    async def _invoke(agent: Agent[None, str]) -> str:
        result = await agent.run(user)
        return result.output.strip().strip('"').strip("'")

    translated = await run_with_fallback(
        get_settings().translator_math_model,
        agent_factory=_math_agent_factory,
        invoke=_invoke,
        metrics=metrics,
        stage=stage,
        agent_name="translator_math",
    )
    return _restore_math(translated, tokens)


async def translate(
    text: str,
    *,
    source: str,
    target: str,
    metrics: TurnMetrics | None = None,
    stage: str = "translate",
) -> str:
    """Auto-route: math-aware if text contains math, otherwise prose."""
    if needs_math_aware(text):
        _log.info("translate_routed", track="math", chars=len(text))
        return await translate_math_aware(
            text, source=source, target=target, metrics=metrics, stage=stage
        )
    _log.info("translate_routed", track="prose", chars=len(text))
    return await translate_prose(text, source=source, target=target, metrics=metrics, stage=stage)
