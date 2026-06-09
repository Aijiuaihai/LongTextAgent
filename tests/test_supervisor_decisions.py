from writing_agent.agents.protocols import CitationAuditReport
from writing_agent.agents.supervisor import SupervisorAgent
from writing_agent.models import ReviewFinding


def test_supervisor_routes_high_severity_to_edit() -> None:
    decision = SupervisorAgent()._run(
        current_round=0,
        max_rounds=2,
        audits=[CitationAuditReport(section_title="A", invalid_citations=1)],
        findings=[
            ReviewFinding(
                issue_type="x",
                severity="high",
                location="doc",
                comment="bad",
                suggestion="fix",
            )
        ],
    )

    assert decision.decision == "edit"
