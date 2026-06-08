from writing_agent.evaluation.llm_judge import parse_judge_output


def test_parse_judge_output_extracts_structured_json() -> None:
    raw = """
```json
{
  "structure_score": 4,
  "logic_score": 4,
  "evidence_score": 3,
  "specificity_score": 4,
  "audience_fit_score": 5,
  "actionability_score": 4,
  "risk_awareness_score": 3,
  "overall_score": 4,
  "comments": "Good structure.",
  "revision_suggestions": ["Add evidence."]
}
```
"""

    result = parse_judge_output(raw)

    assert result["error"] == ""
    assert result["parsed"]["overall_score"] == 4


def test_parse_judge_output_preserves_raw_on_error() -> None:
    result = parse_judge_output("not json")

    assert result["parsed"] is None
    assert result["raw_output"] == "not json"
    assert result["error"]
