"""Embedding provider adapters for local vector RAG."""

from writing_agent.config import Settings, get_settings


def get_embedding_model(settings: Settings | None = None) -> object:
    """Create an embedding model from configured provider settings."""

    resolved = settings or get_settings()
    if resolved.embedding_provider == "ollama":
        try:
            from langchain_ollama import OllamaEmbeddings
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("Install langchain-ollama to use Ollama embeddings.") from exc
        return OllamaEmbeddings(
            base_url=resolved.ollama_base_url,
            model=resolved.ollama_embedding_model,
        )

    if resolved.embedding_provider == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("Install langchain-openai to use OpenAI embeddings.") from exc
        api_key = (
            resolved.openai_api_key.get_secret_value()
            if resolved.openai_api_key is not None
            else None
        )
        return OpenAIEmbeddings(api_key=api_key)

    raise ValueError(f"Unsupported embedding provider: {resolved.embedding_provider}")


def format_embedding_connection_help(settings: Settings | None = None) -> str:
    """Return embedding troubleshooting guidance."""

    resolved = settings or get_settings()
    if resolved.embedding_provider == "ollama":
        return (
            "Ollama embedding call failed. Check `ollama serve`, `ollama list`, "
            f"OLLAMA_BASE_URL={resolved.ollama_base_url}, and "
            f"OLLAMA_EMBEDDING_MODEL={resolved.ollama_embedding_model}."
        )
    return "Embedding call failed. Check OpenAI credentials and model configuration."

