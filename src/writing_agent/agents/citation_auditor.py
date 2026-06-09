"""CitationAuditorAgent."""

from writing_agent.agents.base import AgentSpec, BaseWritingAgent, register_agent
from writing_agent.agents.protocols import CitationAuditReport, SectionAgentDraft
from writing_agent.verification.verifier import verify_citations_in_text

CITATION_AUDITOR_SPEC = register_agent(
    AgentSpec(
        name="citation_auditor",
        responsibility="Verify section citations and report invalid references.",
        input_schema="SectionAgentDraft + optional manifest/collection",
        output_schema="CitationAuditReport",
        prompt_policy="Do not alter facts; validate or mark citation issues.",
        allowed_actions=["verify citations", "report invalid citations", "mark evidence gaps"],
        forbidden_actions=["invent replacement citations", "rewrite factual claims"],
    )
)


class CitationAuditorAgent(BaseWritingAgent):
    """Audit citations in one section draft."""

    spec = CITATION_AUDITOR_SPEC

    def _run(
        self,
        draft: SectionAgentDraft,
        *,
        collection: str | None = None,
    ) -> CitationAuditReport:
        result = verify_citations_in_text(draft.content, collection=collection)
        return CitationAuditReport(
            section_title=draft.title,
            total_citations=result.total_citations,
            valid_citations=result.valid_citations,
            invalid_citations=result.invalid_citations,
            findings=result.findings,
            downgraded_citations=1 if result.insufficient_evidence_count else 0,
        )
