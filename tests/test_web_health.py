from fastapi.testclient import TestClient

from writing_agent.config import Settings
from writing_agent.web.app import create_app


def test_web_health_and_settings_are_secret_safe(tmp_path) -> None:
    settings = Settings(output_dir=tmp_path / "outputs", data_dir=tmp_path / "data")
    client = TestClient(create_app(settings))

    health = client.get("/api/health").json()
    safe_settings = client.get("/api/settings").json()

    assert health["status"] == "ok"
    assert health["llm_provider"] == "ollama"
    assert "api_key" not in str(safe_settings).lower()

