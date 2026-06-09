from fastapi.testclient import TestClient

from writing_agent.config import Settings
from writing_agent.web import app as web_app
from writing_agent.web.app import create_app


def test_web_index_serves_frontend(tmp_path) -> None:
    client = TestClient(
        create_app(Settings(output_dir=tmp_path / "outputs", data_dir=tmp_path / "data"))
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "LongTextAgent Web Console" in response.text


def test_web_generate_compat_creates_job(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(web_app.jobs, "run_job", lambda *args, **kwargs: None)
    client = TestClient(
        create_app(Settings(output_dir=tmp_path / "outputs", data_dir=tmp_path / "data"))
    )

    response = client.post(
        "/api/generate",
        data={
            "topic": "Demo report",
            "type": "report",
            "audience": "reviewers",
            "length": "1000 words",
            "style": "concise",
            "request_text": "Include risks.",
            "output_format": "markdown",
            "rag": "true",
            "rag_mode": "keyword",
            "collection": "",
            "top_k": "3",
            "use_llm": "false",
        },
    )

    assert response.status_code == 200
    assert response.json()["thread_id"].startswith("web-writing-")

