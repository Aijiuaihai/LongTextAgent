from typer.testing import CliRunner

from writing_agent import cli


def test_model_benchmark_cli_dry_run(tmp_path) -> None:
    tasks = tmp_path / "tasks.jsonl"
    tasks.write_text('{"id":"t1","topic":"demo"}\n', encoding="utf-8")

    result = CliRunner().invoke(
        cli.app,
        [
            "model-benchmark",
            "--tasks",
            str(tasks),
            "--models",
            "m1,m2",
            "--embedding-models",
            "e1",
            "--rag-modes",
            "hybrid",
            "--mode",
            "multi",
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert '"total_combinations": 2' in result.output
