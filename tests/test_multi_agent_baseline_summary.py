import json
from pathlib import Path

from writing_agent.config import Settings
from writing_agent.evaluation import batch


def test_multi_agent_batch_summary_tracks_agent_metrics(monkeypatch, tmp_path) -> None:
    tasks_path = tmp_path / "tasks.jsonl"
    tasks_path.write_text(
        json.dumps(
            {
                "id": "task-1",
                "topic": "demo",
                "document_type": "proposal",
                "audience": "reviewers",
                "target_length": "1000 words",
                "style": "formal",
                "source_paths": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    def fake_multi_agent_workflow(initial_state, **kwargs):
        output_dir = Path(initial_state["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "demo.md"
        output_path.write_text(
            "# Demo\n\n## Abstract\n\ntext\n\n"
            "## Plan\n\nbody [source: demo.md#chunk_001]\n\n"
            "## Conclusion\n\ndone\n\n"
            "### References\n\n* [source: demo.md#chunk_001] supports plan\n",
            encoding="utf-8",
        )
        return {
            "output_path": str(output_path),
            "current_round": 2,
            "agent_results": [{"agent_name": "planner"}, {"agent_name": "writer"}],
            "citation_audits": [
                {"repaired_citations": 1, "downgraded_citations": 1},
            ],
            "review_findings": [{"severity": "high"}],
        }

    monkeypatch.setattr(batch, "run_multi_agent_workflow", fake_multi_agent_workflow)
    monkeypatch.setattr(
        batch,
        "verify_citations_in_file",
        lambda *args, **kwargs: type(
            "CitationResult",
            (),
            {"total_citations": 2, "valid_citations": 1},
        )(),
    )

    settings = Settings(output_dir=tmp_path / "outputs")
    result = batch.run_batch_tasks(
        tasks_path,
        output_dir=tmp_path / "baseline",
        rag_mode="hybrid",
        collection="demo",
        output_format="markdown",
        mode="multi",
        max_agent_rounds=2,
        settings=settings,
        run_id="run-1",
    )
    summary = batch.build_baseline_summary(
        batch_result=result,
        rag_mode="hybrid",
        collection="demo",
        settings=settings,
        mode="multi",
        max_agent_rounds=2,
    )

    assert result["success"] == 1
    assert summary["mode"] == "multi"
    assert summary["max_agent_rounds"] == 2
    assert summary["average_agent_count"] == 2
    assert summary["average_rounds"] == 2
    assert summary["average_citation_repair_count"] == 2
    assert summary["average_high_severity_findings"] == 1
    assert summary["average_run_duration_seconds"] > 0
