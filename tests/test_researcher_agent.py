from writing_agent.agents.researcher import ResearcherAgent
from writing_agent.models import SectionPlan, SourceNote


def test_researcher_agent_returns_existing_chunk_ids() -> None:
    note = SourceNote(
        path="data/a.md",
        title="A",
        content_preview="forest knowledge",
        full_text="forest knowledge base retrieval and evaluation",
    )
    section = SectionPlan(
        title="Knowledge Base",
        goal="Explain retrieval",
        key_points=["retrieval"],
    )

    result = ResearcherAgent()._run(section, [note], top_k=1)

    assert result.results
    assert result.results[0].source_path == "data/a.md"
