import json
from pathlib import Path

from writing_agent.config import Settings
from writing_agent.evaluation import model_benchmark


def test_model_benchmark_report_writes_outputs(monkeypatch, tmp_path) -> None:
    tasks = tmp_path / "tasks.jsonl"
    tasks.write_text('{"id":"t1","topic":"demo"}\n', encoding="utf-8")

    def fake_run_batch_tasks(*args, **kwargs):
        run_dir = tmp_path / "batch"
        (run_dir / "task_outputs").mkdir(parents=True, exist_ok=True)
        (run_dir / "task_outputs" / "doc.md").write_text("# Doc\n", encoding="utf-8")
        return {"run_dir": str(run_dir), "success": 1, "failure": 0, "results": []}

    def fake_build_baseline_summary(**kwargs):
        return {
            "average_rule_score": 0.8,
            "average_citation_valid_rate": 0.9,
            "failed_count": 0,
            "average_run_duration_seconds": 1,
            "average_agent_errors": 0,
            "average_fallback_count": 0,
        }

    monkeypatch.setattr(model_benchmark, "run_batch_tasks", fake_run_batch_tasks)
    monkeypatch.setattr(
        model_benchmark,
        "build_baseline_summary",
        fake_build_baseline_summary,
    )

    result = model_benchmark.run_model_benchmark(
        tasks=tasks,
        models="m1",
        embedding_models="e1",
        rag_modes="hybrid",
        output_dir=tmp_path / "bench",
        settings=Settings(output_dir=tmp_path / "outputs"),
    )

    report = json.loads(Path(result["benchmark_report"]).read_text(encoding="utf-8"))
    assert report["success_count"] == 1
    assert result["failed_count"] == 0
