"""LLM provider adapter layer."""

from writing_agent.config import Settings, get_settings


def get_chat_model(settings: Settings | None = None) -> object:
    """Create a chat model from configured provider settings."""

    settings = settings or get_settings()
    message = f"LLM provider adapter is not implemented yet: {settings.llm_provider}"
    raise NotImplementedError(message)
