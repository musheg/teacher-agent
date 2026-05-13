"""Application settings loaded from environment variables (`vars/.env`)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / "vars" / ".env"


class ModelChain(list[str]):
    """A list of `provider:model` identifiers (primary + fallbacks)."""


def _parse_model_chain(raw: str | list[str]) -> ModelChain:
    if isinstance(raw, list):
        return ModelChain([str(m).strip() for m in raw if str(m).strip()])
    items = [m.strip() for m in raw.split(",") if m.strip()]
    return ModelChain(items)


class Settings(BaseSettings):
    """Top-level settings.

    All `*_MODEL` fields accept a comma-separated chain (primary, fallback1, ...).
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── App ────────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"
    service_name: str = "teacher-agents-api"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 60
    jwt_refresh_ttl_days: int = 14

    # ── Data stores ────────────────────────────────────────────────────
    postgres_dsn: str = "postgresql+asyncpg://teacher:teacher@localhost:5432/teacher"
    redis_url: str = "redis://localhost:6379/0"

    context_max_turns: int = 20
    context_summary_threshold_tokens: int = 4000

    # ── Google STT ─────────────────────────────────────────────────────
    google_application_credentials: str | None = None
    stt_language: str = "hy-AM"
    stt_model: str = "chirp_2"
    stt_location: str = "asia-southeast1"
    stt_project_id: str | None = None

    # ── TTS ────────────────────────────────────────────────────────────
    tts_provider: Literal["openai", "azure", "elevenlabs", "google"] = "openai"
    tts_voice: str = "alloy"
    openai_tts_model: str = "gpt-4o-mini-tts"
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None
    azure_tts_voice: str = "hy-AM-AnahitNeural"
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str | None = None

    # ── LLM provider keys ──────────────────────────────────────────────
    openai_api_key: str | None = None
    google_api_key: str | None = None
    anthropic_api_key: str | None = None

    # ── Per-agent model chains (primary,fallback1,fallback2) ───────────
    # `NoDecode` keeps pydantic-settings from JSON-parsing the env value so
    # our `field_validator(mode="before")` receives the raw comma-separated
    # string.
    tutor_model: Annotated[ModelChain, NoDecode] = Field(
        default_factory=lambda: ModelChain(["openai:gpt-5.4"])
    )
    solver_model: Annotated[ModelChain, NoDecode] = Field(
        default_factory=lambda: ModelChain(["openai:gpt-5.4-mini"])
    )
    curriculum_model: Annotated[ModelChain, NoDecode] = Field(
        default_factory=lambda: ModelChain(["openai:gpt-5.4-mini"])
    )
    assessment_model: Annotated[ModelChain, NoDecode] = Field(
        default_factory=lambda: ModelChain(["openai:gpt-5.4-mini"])
    )
    visualization_model: Annotated[ModelChain, NoDecode] = Field(
        default_factory=lambda: ModelChain(["openai:gpt-5.4-mini"])
    )
    translator_prose_model: Annotated[ModelChain, NoDecode] = Field(
        default_factory=lambda: ModelChain(["openai:gpt-4o-mini"])
    )
    translator_math_model: Annotated[ModelChain, NoDecode] = Field(
        default_factory=lambda: ModelChain(["openai:gpt-5.4-mini"])
    )
    speech_model: Annotated[ModelChain, NoDecode] = Field(
        default_factory=lambda: ModelChain(["openai:gpt-4o-mini"])
    )
    safety_model: Annotated[ModelChain, NoDecode] = Field(
        default_factory=lambda: ModelChain(["openai:gpt-4o-mini"])
    )
    summarizer_model: Annotated[ModelChain, NoDecode] = Field(
        default_factory=lambda: ModelChain(["openai:gpt-4o-mini"])
    )
    moderation_model: str = "omni-moderation-latest"

    # ── Limits & fallbacks ─────────────────────────────────────────────
    max_audio_seconds: int = 30
    max_turns_per_session: int = 200
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 2
    feature_offline_fallback: bool = True

    # ── CORS / frontend ────────────────────────────────────────────────
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    # ── Bootstrap admin ────────────────────────────────────────────────
    create_admin_email: str | None = None
    create_admin_password: str | None = None

    @field_validator(
        "tutor_model",
        "solver_model",
        "curriculum_model",
        "assessment_model",
        "visualization_model",
        "translator_prose_model",
        "translator_math_model",
        "speech_model",
        "safety_model",
        "summarizer_model",
        mode="before",
    )
    @classmethod
    def _coerce_model_chain(cls, v: str | list[str] | ModelChain) -> ModelChain:
        if isinstance(v, ModelChain):
            return v
        return _parse_model_chain(v)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _coerce_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
