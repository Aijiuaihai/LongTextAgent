"""ReviewerAgent."""

from writing_agent.agents.base import AgentSpec, BaseWritingAgent, register_agent
from writing_agent.agents.protocols import CitationAuditReport, SectionAgentDraft
from writing_agent.models import ReviewFinding, WritingRequest

REVIEWER_SPEC = register_agent(
    AgentSpec(
        name="reviewer",
        responsibility="Review structure, logic, repetition, specificity, risk, and evidence gaps.",
        input_schema="WritingRequest + list[SectionAgentDraft] + list[CitationAuditReport]",
        output_schema="list[ReviewFinding]",
        prompt_policy="Produce findings only; do not rewrite the document.",
        allowed_actions=["identify findings", "assign severity", "suggest targeted fixes"],
        forbidden_actions=["rewrite whole draft", "invent evidence"],
    )
)


class ReviewerAgent(BaseWritingAgent):
    """Review multi-agent drafts."""

    spec = REVIEWER_SPEC

    def _run(
        self,
        request: WritingRequest,
        drafts: list[SectionAgentDraft],
        audits: list[CitationAuditReport],
    ) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []
        if any(audit.invalid_citations for audit in audits):
            findings.append(
                ReviewFinding(
                    issue_type="citation_invalid",
                    severity="high",
                    location="citations",
                    comment="Some citations failed verification.",
                    suggestion="Repair invalid citations or downgrade to insufficient evidence.",
                )
            )
        if any(draft.insufficient_evidence for draft in drafts):
            findings.append(
                ReviewFinding(
                    issue_type="evidence_gap",
                    severity="medium",
                    location="sections",
                    comment="At least one section lacks retrieved evidence.",
                    suggestion="Keep evidence-gap notes visible or add sources.",
                )
            )
        if request.document_type.value in {"proposal", "plan"} and len(drafts) < 3:
            findings.append(
                ReviewFinding(
                    issue_type="structure_gap",
                    severity="high",
                    location="outline",
                    comment="Plan/proposal documents need sufficient implementation structure.",
                    suggestion=(
                        "Add scope, technical route, milestones, resources, "
                        "risks, and acceptance."
                    ),
                )
            )
        return findings
