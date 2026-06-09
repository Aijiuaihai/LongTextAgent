from writing_agent.agents.protocols import EvidencePack, SectionWritingTask
from writing_agent.agents.writer import WriterAgent
from writing_agent.models import SectionPlan
from writing_agent.rag.models import RetrievalResult


def test_writer_agent_uses_required_citation_format() -> None:
    evidence = EvidencePack(
        section_title="A",
        query="q",
        results=[
            RetrievalResult(
                chunk_id="data/a.md#chunk-1",
                source_path="data/a.md",
                score=1,
                text="evidence",
                metadata={},
            )
        ],
    )
    task = SectionWritingTask(section_plan=SectionPlan(title="A", goal="G"), evidence_pack=evidence)

    draft = WriterAgent()._run(task)

    assert "[source: data/a.md#data/a.md#chunk-1]" in draft.content
    assert draft.insufficient_evidence is False

