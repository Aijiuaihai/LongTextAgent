from writing_agent.config import Settings


def test_default_config_loads() -> None:
    settings = Settings()

    assert settings.llm_provider == "ollama"
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_model == "qwen3.6:35b"
    assert settings.output_dir.as_posix() == "outputs"

