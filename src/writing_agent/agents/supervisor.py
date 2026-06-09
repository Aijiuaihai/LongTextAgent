"""SupervisorAgent."""

from writing_agent.agents.base import AgentSpec, BaseWritingAgent, register_agent
from writing_agent.agents.protocols import CitationAuditReport, SupervisorDecision
from writing_agent.models import ReviewFinding

SUPERVISOR_SPEC = register_agent(
    AgentSpec(
        name="supervisor",
        responsibility="Route finite multi-agent workflow and prevent uncontrolled loops.",
        input_schema="round + audits + review findings + max_rounds",
        output_schema="SupervisorDecision",
        prompt_policy="Route only; do not write body text.",
        allowed_actions=["route to editor", "route to formatter", "record warnings"],
        forbidden_actions=["write body", "ignore citation failures", "loop indefinitely"],
    )
)


class SupervisorAgent(BaseWritingAgent):
    """Decide whether to edit or format."""

    spec = SUPERVISOR_SPEC

    def _run(
        self,
        *,
        current_round: int,
        max_rounds: int,
        audits: list[CitationAuditReport],
        findings: list[ReviewFinding],
    ) -> SupervisorDecision:
        invalid = sum(audit.invalid_citations for audit in audits)
        high = sum(1 for finding in findings if finding.severity == "high")
        if current_round < max_rounds and (invalid > 0 or high > 0):
            return SupervisorDecision(
                decision="edit",
                reason="High severity findings or invalid citations require one bounded edit pass.",
                current_round=current_round,
                high_severity_findings=high,
                invalid_citations=invalid,
            )
        return SupervisorDecision(
            decision="format",
            reason="No blocking findings remain or max rounds reached.",
            current_round=current_round,
            high_severity_findings=high,
            invalid_citations=invalid,
        )

