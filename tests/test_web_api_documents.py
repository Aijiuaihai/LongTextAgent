from fastapi.testclient import TestClient

from writing_agent.config import Settings
from writing_agent.web.app import create_app


def test_documents_api_lists_previews_and_evaluates_markdown(tmp_path) -> None:
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    document = output_dir / "demo.md"
    document.write_text("# Demo\n\n## 摘要\n\ntext\n\n## 结论\n\ntext", encoding="utf-8")
    client = TestClient(create_app(Settings(output_dir=output_dir, data_dir=tmp_path / "data")))

    row = client.get("/api/documents").json()[0]
    preview = client.get(f"/api/documents/{row['document_id']}/preview").json()
    evaluation = client.post(
        f"/api/documents/{row['document_id']}/evaluate",
        json={"llm_judge": False},
    ).json()

    assert preview["type"] == "markdown"
    assert "rule_metrics" in evaluation

