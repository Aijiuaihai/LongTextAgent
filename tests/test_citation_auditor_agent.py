from writing_agent.agents.citation_auditor import CitationAuditorAgent
from writing_agent.agents.protocols import SectionAgentDraft


def test_citation_auditor_agent_flags_invalid_citations() -> None:
    draft = SectionAgentDraft(
        title="A",
        content="## A\n\n### 参考依据\n\n* [source: data/a.md#fake]",
    )

    report = CitationAuditorAgent()._run(draft)

    assert report.invalid_citations == 1

