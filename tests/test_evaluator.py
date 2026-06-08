from writing_agent.evaluation.metrics import evaluate_text


def test_evaluate_text_reports_quality_metrics() -> None:
    markdown = """# Demo

## 摘要

这是摘要。

## 方案

形成闭环，显著提升智能化水平。

## 结论

本节资料依据不足。

### 参考依据

- source.md#chunk-1
"""

    result = evaluate_text(markdown)

    assert result["characters"] > 0
    assert result["section_count"] >= 3
    assert result["has_abstract"] is True
    assert result["has_conclusion"] is True
    assert result["has_references"] is True
    assert result["insufficient_evidence_count"] == 1
    assert result["risk_terms"]["形成闭环"] == 1

