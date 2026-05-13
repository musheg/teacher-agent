"""Domain exceptions raised by services and agents."""

from __future__ import annotations


class TeacherAgentsError(Exception):
    """Base for all domain errors."""


class ConfigurationError(TeacherAgentsError):
    """Misconfiguration that prevents the app from running correctly."""


class UpstreamError(TeacherAgentsError):
    """An external dependency (LLM, STT, TTS, DB) failed."""

    def __init__(self, upstream: str, message: str, *, retryable: bool = True) -> None:
        super().__init__(f"[{upstream}] {message}")
        self.upstream = upstream
        self.retryable = retryable


class CircuitOpenError(UpstreamError):
    """The circuit breaker is open and the call was short-circuited."""

    def __init__(self, upstream: str) -> None:
        super().__init__(upstream, "circuit open", retryable=False)


class AllFallbacksFailedError(UpstreamError):
    """Every model/provider in the fallback chain failed."""

    def __init__(self, upstream: str, attempts: list[str]) -> None:
        super().__init__(upstream, f"all fallbacks exhausted: {attempts}", retryable=False)
        self.attempts = attempts


class AuthError(TeacherAgentsError):
    """Authentication / authorization failure."""


class SafetyBlockError(TeacherAgentsError):
    """Content was blocked by the Safety agent."""

    def __init__(self, reason: str, categories: list[str] | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.categories = categories or []
