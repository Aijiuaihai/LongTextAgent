import json

from writing_agent.evaluation.compare import (
    compare_baseline_summaries,
    render_baseline_comparison,
)


def _write_summary(path, **overrides) -> None:
    data = {
        "commit_hash": "abc",
        "model_name": "model",
        "embedding_model": "embed",
        "rag_mode": "hybrid",
        "collection": "demo",
        "task_count": 2,
        "success_count": 2,
        "failed_count": 0,
        "average_rule_score": 0.9,
        "average_citation_valid_rate": 0.95,
        "average_insufficient_evidence_count": 1.0,
    }
    data.update(overrides)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_compare_baseline_summaries_flags_regressions(tmp_path) -> None:
    base = tmp_path / "base.json"
    candidate = tmp_path / "candidate.json"
    _write_summary(base)
    _write_summary(
        candidate,
        average_rule_score=0.8,
        average_citation_valid_rate=0.9,
        average_insufficient_evidence_count=1.3,
        failed_count=1,
    )

    result = compare_baseline_summaries(base, candidate)
    rendered = render_baseline_comparison(result)

    assert result.status == "fail"
    assert result.delta_rule_score < 0
    assert any(flag.metric == "failed_count" for flag in result.regression_flags)
    assert rendered["status"] == "fail"

