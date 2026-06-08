import sys
import types

from writing_agent.config import Settings
from writing_agent.rag.embeddings import get_embedding_model


def test_get_embedding_model_uses_ollama_settings(monkeypatch) -> None:
    captured = {}

    class FakeOllamaEmbeddings:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

    fake_module = types.SimpleNamespace(OllamaEmbeddings=FakeOllamaEmbeddings)
    monkeypatch.setitem(sys.modules, "langchain_ollama", fake_module)

    settings = Settings(
        embedding_provider="ollama",
        ollama_base_url="http://example.test:11434",
        ollama_embedding_model="bge-m3",
    )

    model = get_embedding_model(settings)

    assert isinstance(model, FakeOllamaEmbeddings)
    assert captured["base_url"] == "http://example.test:11434"
    assert captured["model"] == "bge-m3"

