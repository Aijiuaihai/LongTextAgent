import json

from pydantic import BaseModel

from writing_agent.agents.retry import run_with_structured_retry
from writing_agent.models import ReviewFinding


class ReviewOutput(BaseModel):
    findings: list[ReviewFinding]


def test_reviewer_agent_structured_retry_validates_findings_wrapper() -> None:
    payload = {
        "findings": [
            {
                "issue_type": "evidence_gap",
                "severity": "medium",
                "location": "section",
                "comment": "Evidence is thin.",
                "suggestion": "Add sources or keep insufficiency marker.",
            }
        ]
    }

    result = run_with_structured_retry(
        "reviewer",
        lambda prompt=None: json.dumps(payload),
        ReviewOutput,
    )

    assert result.status == "success"
    assert result.output["value"]["findings"][0]["issue_type"] == "evidence_gap"
