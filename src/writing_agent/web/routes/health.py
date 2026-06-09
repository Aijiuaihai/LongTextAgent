"""Health and settings endpoints."""

import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from fastapi import APIRouter, Request

from writing_agent.llm import get_chat_model
from writing_agent.observability.langsmith import configure_langsmith, is_langsmith_enabled

router = APIRouter()


def _project_version() -> str:
    try:
        return version("writing-agent")
    except PackageNotFoundError:
        return "0.1.0"


@router.get("/health")
def health(request: Request) -> dict[str, Any]:
    """Return a secret-safe health payload."""

    settings = request.app.state.settings
    model_name = (
        settings.ollama_model
        if settings.llm_provider == "ollama"
        else settings.openai_model
    )
    return {
        "status": "ok",
        "python_version": ".".join(str(part) for part in sys.version_info[:3]),
        "project_version": _project_version(),
        "llm_provider": settings.llm_provider,
        "model_name": model_name or "",
        "output_dir": str(settings.output_dir),
        "data_dir": str(settings.data_dir),
    }


@router.get("/settings")
def settings(request: Request) -> dict[str, str | None]:
    """Return secret-safe settings."""

    return request.app.state.settings.safe_summary()


@router.get("/settings/trace-check")
def trace_check(request: Request) -> dict[str, object]:
    """Return secret-safe LangSmith trace check payload."""

    settings = request.app.state.settings
    warnings = configure_langsmith(settings)
    return {
        "langsmith_tracing": settings.langsmith_tracing,
        "langsmith_project": settings.langsmith_project,
        "api_key_detected": settings.langsmith_api_key is not None,
        "will_upload_trace": is_langsmith_enabled(settings),
        "warnings": warnings,
    }


@router.post("/settings/check-model")
def check_model(request: Request) -> dict[str, object]:
    """Call the configured model once and return a short secret-safe result."""

    settings = request.app.state.settings
    model = get_chat_model(settings)
    response = model.invoke("Reply with a short readiness confirmation.")
    content = getattr(response, "content", response)
    return {
        "provider": settings.llm_provider,
        "model": settings.ollama_model
        if settings.llm_provider == "ollama"
        else settings.openai_model,
        "response_preview": str(content)[:200],
    }
