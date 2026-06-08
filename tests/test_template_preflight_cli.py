from docx import Document
from typer.testing import CliRunner

from writing_agent import cli


def test_template_preflight_cli_json(tmp_path) -> None:
    runner = CliRunner()
    template = tmp_path / "template.docx"
    document = Document()
    document.add_paragraph("{{title}} {{topic}} {{document_type}} {{audience}} {{generated_at}}")
    document.save(str(template))

    result = runner.invoke(
        cli.app,
        ["template", "preflight", "--template", str(template), "--json"],
    )

    assert result.exit_code == 0
    assert '"status": "warning"' in result.output
