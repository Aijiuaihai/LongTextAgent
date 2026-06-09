import json

from writing_agent.agents.protocols import SectionAgentDraft
from writing_agent.agents.retry import run_with_structured_retry


def test_writer_agent_structured_retry_validates_section_draft() -> None:
    payload = {
        "title": "Scope",
        "content": "## Scope\n\nText\n\n### References\n\n* 本节资料依据不足",
        "citations": [],
        "evidence_used": [],
        "insufficient_evidence": True,
    }

    result = run_with_structured_retry(
        "writer",
        lambda prompt=None: json.dumps(payload),
        SectionAgentDraft,
    )

    assert result.status == "success"
    assert result.output["value"]["title"] == "Scope"
    assert result.output["value"]["insufficient_evidence"] is True
