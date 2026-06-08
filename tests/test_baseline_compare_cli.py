import json

from typer.testing import CliRunner

from writing_agent import cli


def _write(path, failed_count: int) -> None:
    path.write_text(
        json.dumps(
            {
                "commit_hash": "abc",
                "model_name": "model",
                "embedding_model": "embed",
                "rag_mode": "hybrid",
                "collection": "demo",
                "task_count": 1,
                "success_count": 1 - failed_count,
                "failed_count": failed_count,
                "average_rule_score": 0.9,
                "average_citation_valid_rate": 0.9,
                "average_insufficient_evidence_count": 0,
            }
        ),
        encoding="utf-8",
    )


def test_baseline_compare_cli_fails_on_fail_regression(tmp_path) -> None:
    runner = CliRunner()
    base = tmp_path / "base.json"
    candidate = tmp_path / "candidate.json"
    _write(base, failed_count=0)
    _write(candidate, failed_count=1)

    result = runner.invoke(
        cli.app,
        [
            "baseline-compare",
            "--base",
            str(base),
            "--candidate",
            str(candidate),
            "--fail-on-regression",
        ],
    )

    assert result.exit_code == 1
