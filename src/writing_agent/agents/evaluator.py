"""EvaluatorAgent."""

from writing_agent.agents.base import AgentSpec, BaseWritingAgent, register_agent
from writing_agent.evaluation.evaluator import evaluate_text
from writing_agent.models import FinalDocument
from writing_agent.verification.verifier import verify_citations_in_text

EVALUATOR_SPEC = register_agent(
    AgentSpec(
        name="evaluator",
        responsibility="Evaluate quality and citation status without modifying content.",
        input_schema="FinalDocument + optional collection",
        output_schema="dict",
        prompt_policy="Evaluate only; never edit document text.",
        allowed_actions=["rule evaluation", "citation verification"],
        forbidden_actions=["rewrite text", "repair citations"],
    )
)


class EvaluatorAgent(BaseWritingAgent):
    """Run deterministic final checks."""

    spec = EVALUATOR_SPEC

    def _run(self, document: FinalDocument, *, collection: str | None = None) -> dict[str, object]:
        citations = verify_citations_in_text(document.markdown, collection=collection)
        return {
            "rule_metrics": evaluate_text(document.markdown),
            "citation_verification": citations.model_dump(mode="json"),
        }

