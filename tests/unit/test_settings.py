from app.settings import Settings, get_settings


def test_settings_loads_defaults() -> None:
    s = Settings()
    assert s.app_env == "development"
    assert isinstance(s.tutor_model, list)
    assert s.tutor_model[0].startswith("openai:")


def test_model_chain_parses_csv(monkeypatch) -> None:
    monkeypatch.setenv("TUTOR_MODEL", "openai:gpt-5.4,google-gla:gemini-2.5-pro")
    get_settings.cache_clear()
    s = get_settings()
    assert s.tutor_model == ["openai:gpt-5.4", "google-gla:gemini-2.5-pro"]
