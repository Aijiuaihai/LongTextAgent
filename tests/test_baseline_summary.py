from writing_agent.config import Settings
from writing_agent.evaluation.batch import build_baseline_summary


def test_build_baseline_summary(tmp_path) -> None:
    run_dir = tmp_path / "baseline" / "run"
    task_outputs = run_dir / "task_outputs"
    task_outputs.mkdir(parents=True)
    (task_outputs / "doc.md").write_text(
        "# Doc\n\n## 摘要\n\ntext\n\n## 结论\n\n本节资料依据不足。\n\n### 参考依据\n\n- x",
        encoding="utf-8",
    )
    batch_result = {"run_dir": str(run_dir), "success": 1, "failure": 0}
    settings = Settings(output_dir=tmp_path / "outputs")

    summary = build_baseline_summary(
        batch_result=batch_result,
        rag_mode="hybrid",
        collection="demo",
        settings=settings,
    )

    assert summary["task_count"] == 1
    assert summary["success_count"] == 1
    assert "average_rule_score" in summary
