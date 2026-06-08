"""LangSmith configuration helpers."""

import os

from writing_agent.config import Settings, get_settings


def is_langsmith_enabled(settings: Settings | None = None) -> bool:
    """Return whether LangSmith tracing should be enabled."""

    resolved = settings or get_settings()
    return bool(resolved.langsmith_tracing and resolved.langsmith_api_key)


def get_langsmith_project(settings: Settings | None = None) -> str:
    """Return configured LangSmith project."""

    return (settings or get_settings()).langsmith_project


def configure_langsmith(settings: Settings | None = None) -> list[str]:
    """Configure LangSmith environment variables without exposing secrets."""

    resolved = settings or get_settings()
    warnings: list[str] = []
    if not resolved.langsmith_tracing:
        os.environ["LANGSMITH_TRACING"] = "false"
        return warnings
    if resolved.langsmith_api_key is None:
        warnings.append("LANGSMITH_TRACING is true but LANGSMITH_API_KEY is not set.")
        os.environ["LANGSMITH_TRACING"] = "false"
        return warnings
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = resolved.langsmith_project
    os.environ["LANGSMITH_API_KEY"] = resolved.langsmith_api_key.get_secret_value()
    if resolved.langsmith_endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = resolved.langsmith_endpoint
    return warnings

