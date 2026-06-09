from writing_agent.config import Settings
from writing_agent.evaluation.batch import build_baseline_summary


def test_baseline_summary_includes_agent_metric_averages(tmp_path) -> None:
    run_dir = tmp_path / "baseline" / "run"
    task_outputs = run_dir / "task_outputs"
    task_outputs.mkdir(parents=True)
    (task_outputs / "doc.md").write_text(
        "# Doc\n\n## Abstract\n\ntext\n\n## Conclusion\n\ntext\n",
        encoding="utf-8",
    )
    batch_result = {
        "run_dir": str(run_dir),
        "success": 1,
        "failure": 0,
        "results": [
            {
                "status": "success",
                "agent_errors": 2,
                "agent_warnings": 3,
                "fallback_count": 1,
                "citation_auditor_invalid_count": 4,
                "supervisor_rounds_used": 2,
            }
        ],
    }

    summary = build_baseline_summary(
        batch_result=batch_result,
        rag_mode="hybrid",
        collection="demo",
        settings=Settings(output_dir=tmp_path / "outputs"),
        mode="multi",
        max_agent_rounds=2,
    )

    assert summary["average_agent_errors"] == 2
    assert summary["average_agent_warnings"] == 3
    assert summary["average_fallback_count"] == 1
    assert summary["average_citation_auditor_invalid_count"] == 4
    assert summary["average_supervisor_rounds_used"] == 2
