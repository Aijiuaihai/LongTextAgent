from typer.testing import CliRunner

from writing_agent import cli


def test_batch_rerun_failed_command(monkeypatch, tmp_path) -> None:
    failed = tmp_path / "failed_tasks.jsonl"
    failed.write_text('{"id":"retry","topic":"Retry"}\n', encoding="utf-8")
    called = {}

    def fake_run_batch_tasks(tasks_path, **kwargs):
        called["tasks_path"] = tasks_path
        called["output_dir"] = kwargs["output_dir"]
        return {"run_id": "r", "success": 1, "failure": 0, "run_dir": "out", "results": []}

    monkeypatch.setattr(cli, "run_batch_tasks", fake_run_batch_tasks)
    result = CliRunner().invoke(
        cli.app,
        [
            "batch-rerun-failed",
            "--failed-tasks",
            str(failed),
            "--output-dir",
            str(tmp_path / "rerun"),
        ],
    )

    assert result.exit_code == 0
    assert called["tasks_path"] == failed
