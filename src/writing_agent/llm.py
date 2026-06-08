"""LLM provider adapter layer."""

from writing_agent.config import Settings, get_settings


def get_chat_model(settings: Settings | None = None) -> object:
    """Create a chat model from configured provider settings."""

    settings = settings or get_settings()
    if settings.llm_provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("Install langchain-ollama to use the Ollama provider.") from exc

        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=0.2,
        )

    if settings.llm_provider in {"openai_compatible", "openai"}:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:  # pragma: no cover - dependency guard
            message = "Install langchain-openai to use OpenAI-compatible providers."
            raise RuntimeError(message) from exc

        api_key = (
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key is not None
            else None
        )
        kwargs: dict[str, str | float | None] = {
            "api_key": api_key,
            "model": settings.openai_model,
            "temperature": 0.2,
        }
        if settings.llm_provider == "openai_compatible":
            kwargs["base_url"] = settings.openai_base_url
        return ChatOpenAI(**kwargs)

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


def format_connection_help(settings: Settings | None = None) -> str:
    """Return provider-specific troubleshooting guidance."""

    settings = settings or get_settings()
    if settings.llm_provider == "ollama":
        return (
            "Ollama connection failed. Check that `ollama serve` is running, "
            f"model `{settings.ollama_model}` is available, and "
            f"`OLLAMA_BASE_URL` points to the correct 11434 endpoint "
            f"({settings.ollama_base_url})."
        )
    return "Model connection failed. Check OPENAI_BASE_URL, OPENAI_MODEL, and credentials."
