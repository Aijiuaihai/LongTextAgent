from docx import Document
from fastapi.testclient import TestClient

from writing_agent.config import Settings
from writing_agent.web.app import create_app


def test_template_preflight_api(tmp_path) -> None:
    template = tmp_path / "template.docx"
    document = Document()
    document.add_paragraph("{{title}} {{topic}} {{document_type}} {{audience}} {{generated_at}}")
    document.save(str(template))
    client = TestClient(
        create_app(Settings(output_dir=tmp_path / "outputs", data_dir=tmp_path / "data"))
    )

    result = client.post(
        "/api/templates/preflight",
        json={"template_path": str(template)},
    ).json()

    assert result["status"] == "warning"

