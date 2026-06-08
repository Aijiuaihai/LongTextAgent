from typer.testing import CliRunner

from writing_agent import cli
from writing_agent.verification.repair import CitationRepairResult
from writing_agent.verification.verifier import CitationVerificationResult


def test_repair_citations_cli_smoke(tmp_path, monkeypatch) -> None:
    runner = CliRunner()
    markdown = tmp_path / "doc.md"
    markdown.write_text("# Demo", encoding="utf-8")

    verification = CitationVerificationResult(
        total_citations=1,
        valid_citations=0,
        invalid_citations=1,
        overall_status="fail",
    )
    repaired = CitationRepairResult(
        file_path=str(markdown),
        mode="conservative",
        repaired_text="# Demo",
        output_path=str(tmp_path / "doc.repaired.md"),
        downgraded_count=1,
        before=verification,
        after=verification.model_copy(update={"invalid_citations": 0, "overall_status": "pass"}),
    )
    monkeypatch.setattr(cli, "repair_citations_in_file", lambda *args, **kwargs: repaired)

    result = runner.invoke(
        cli.app,
        [
            "repair-citations",
            "--file",
            str(markdown),
            "--collection",
            "demo",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert "downgraded_count" in result.output
