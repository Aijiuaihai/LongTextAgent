from writing_agent.config import Settings
from writing_agent.observability.langsmith import (
    configure_langsmith,
    get_langsmith_project,
    is_langsmith_enabled,
)


def test_langsmith_disabled_by_default(monkeypatch) -> None:
    settings = Settings(langsmith_tracing=False, langsmith_project="local")

    warnings = configure_langsmith(settings)

    assert warnings == []
    assert is_langsmith_enabled(settings) is False
    assert get_langsmith_project(settings) == "local"
    assert "LANGSMITH_API_KEY" not in warnings


def test_langsmith_warns_without_key() -> None:
    settings = Settings(langsmith_tracing=True, langsmith_api_key=None)

    warnings = configure_langsmith(settings)

    assert warnings
    assert is_langsmith_enabled(settings) is False

