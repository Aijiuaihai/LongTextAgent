import os

import pytest

from writing_agent.config import Settings
from writing_agent.llm import get_chat_model

pytestmark = [pytest.mark.integration, pytest.mark.ollama, pytest.mark.slow]


def _enabled(name: str) -> bool:
    return os.getenv(name, "").lower() == "true"


def test_ollama_model_responds() -> None:
    if not (_enabled("RUN_INTEGRATION_TESTS") and _enabled("RUN_OLLAMA_TESTS")):
        pytest.skip("Set RUN_INTEGRATION_TESTS=true and RUN_OLLAMA_TESTS=true.")

    settings = Settings()
    model = get_chat_model(settings)
    response = model.invoke("Reply with one short readiness sentence.")

    assert str(getattr(response, "content", response)).strip()
