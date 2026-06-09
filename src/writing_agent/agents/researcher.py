"""ResearcherAgent."""

from writing_agent.agents.base import AgentSpec, BaseWritingAgent, register_agent
from writing_agent.agents.protocols import EvidencePack
from writing_agent.models import SectionPlan, SourceNote
from writing_agent.rag.index import build_local_index
from writing_agent.rag.models import RetrievalResult
from writing_agent.rag.retriever import retrieve

RESEARCHER_SPEC = register_agent(
    AgentSpec(
        name="researcher",
        responsibility="Retrieve evidence for section tasks without writing prose.",
        input_schema="SectionPlan + list[SourceNote] + top_k",
        output_schema="EvidencePack",
        prompt_policy="Return only existing source_path/chunk_id evidence.",
        allowed_actions=["retrieve chunks", "mark evidence gaps"],
        forbidden_actions=["write body", "invent citations", "generate final conclusions"],
    )
)


class ResearcherAgent(BaseWritingAgent):
    """Retrieve source evidence for one section."""

    spec = RESEARCHER_SPEC

    def _run(
        self,
        section: SectionPlan,
        source_notes: list[SourceNote],
        *,
        top_k: int = 5,
    ) -> EvidencePack:
        query = " ".join([section.title, section.goal, *section.key_points])
        chunks = build_local_index(source_notes)
        raw_results = retrieve(query, chunks, top_k=top_k) if chunks else []
        results = [
            item
            if isinstance(item, RetrievalResult)
            else RetrievalResult(
                chunk_id=item.chunk_id,
                source_path=item.source_path,
                score=1.0,
                text=item.text,
                metadata=item.metadata,
            )
            for item in raw_results
        ]
        return EvidencePack(
            section_title=section.title,
            query=query,
            results=results,
            insufficient_evidence=not bool(results),
            notes=[] if results else ["No relevant source chunks were retrieved."],
        )
