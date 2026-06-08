from pathlib import Path

from writing_agent.evaluation.batch import evaluate_batch_directory, load_jsonl_tasks


def test_load_jsonl_tasks(tmp_path) -> None:
    path = tmp_path / "tasks.jsonl"
    path.write_text('{"id": "a", "topic": "Topic"}\n', encoding="utf-8")

    tasks = load_jsonl_tasks(path)

    assert tasks[0]["id"] == "a"


def test_evaluate_batch_directory_summarizes_markdown(tmp_path) -> None:
    (tmp_path / "a.md").write_text(
        "# A\n\n## 摘要\n\ntext\n\n## 结论\n\n本节资料依据不足。\n\n### 参考依据\n\n- x",
        encoding="utf-8",
    )
    (tmp_path / "b.md").write_text(
        "# B\n\n## 摘要\n\ntext\n\n## 结论\n\n形成闭环。\n\n### 参考依据\n\n- y",
        encoding="utf-8",
    )

    result = evaluate_batch_directory(Path(tmp_path))

    assert result["file_count"] == 2
    assert result["summary"]["average_sections"] >= 3
    assert result["summary"]["risk_term_total"] == 1
