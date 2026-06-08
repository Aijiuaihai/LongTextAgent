import json

from writing_agent.config import Settings
from writing_agent.evaluation import batch


def test_batch_run_writes_report_and_failed_tasks(tmp_path, monkeypatch) -> None:
    tasks = tmp_path / "tasks.jsonl"
    tasks.write_text(
        '{"id":"ok","topic":"OK"}\n{"id":"bad","document_type":"proposal"}\n',
        encoding="utf-8",
    )

    def fake_run_workflow(state, **kwargs):
        output = tmp_path / "out.md"
        output.write_text("# OK", encoding="utf-8")
        return {"output_path": str(output)}

    monkeypatch.setattr(batch, "run_writing_workflow", fake_run_workflow)

    result = batch.run_batch_tasks(
        tasks,
        output_dir=tmp_path / "batch",
        settings=Settings(output_dir=tmp_path / "outputs"),
        run_id="run-1",
    )

    run_dir = tmp_path / "batch" / "run-1"
    report = json.loads((run_dir / "batch_report.json").read_text(encoding="utf-8"))
    failed = (run_dir / "failed_tasks.jsonl").read_text(encoding="utf-8")
    assert result["success"] == 1
    assert result["failure"] == 1
    assert report["total_tasks"] == 2
    assert '"id": "bad"' in failed

