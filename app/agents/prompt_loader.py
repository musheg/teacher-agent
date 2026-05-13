"""Utility for loading prompt markdown files shipped with the package."""

from __future__ import annotations

from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=64)
def load_prompt(name: str) -> str:
    """Load `app/agents/prompts/{name}.md`."""
    pkg = resources.files("app.agents.prompts")
    return (pkg / f"{name}.md").read_text(encoding="utf-8")
