from docx import Document

from writing_agent.tools.export import export_docx_from_template


def test_export_docx_from_template_appends_body_when_missing_placeholder(tmp_path) -> None:
    template = tmp_path / "template.docx"
    document = Document()
    document.add_paragraph("{{title}}")
    document.save(str(template))

    output, warnings = export_docx_from_template(
        "# Generated",
        template_path=template,
        output_dir=tmp_path,
        title="Template Plan",
        metadata={"topic": "Topic"},
    )

    assert output.exists()
    assert warnings
