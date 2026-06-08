from fastapi.testclient import TestClient

from writing_agent.config import Settings
from writing_agent.web import app as web_app
from writing_agent.web.app import WebGenerationResult, create_app


def test_web_index_serves_frontend(tmp_path) -> None:
    client = TestClient(create_app(Settings(output_dir=tmp_path / "outputs")))

    response = client.get("/")

    assert response.status_code == 200
    assert "LongTextAgent" in response.text


def test_web_generate_uses_workflow_bridge(tmp_path, monkeypatch) -> None:
    def fake_generate_document(**kwargs):
        return WebGenerationResult(
            thread_id="web-writing-test",
            topic=kwargs["topic"],
            output_path=str(tmp_path / "outputs" / "demo.md"),
            output_paths={"markdown": str(tmp_path / "outputs" / "demo.md")},
            errors=[],
        )

    monkeypatch.setattr(web_app, "_generate_document", fake_generate_document)
    client = TestClient(create_app(Settings(output_dir=tmp_path / "outputs")))

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
    assert response.json()["thread_id"] == "web-writing-test"
