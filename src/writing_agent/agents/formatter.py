"""FormatterAgent."""

from writing_agent.agents.base import AgentSpec, BaseWritingAgent, register_agent
from writing_agent.agents.protocols import SectionAgentDraft
from writing_agent.models import FinalDocument, WritingPlan, WritingRequest

FORMATTER_SPEC = register_agent(
    AgentSpec(
        name="formatter",
        responsibility="Assemble final markdown without changing section content.",
        input_schema="WritingRequest + WritingPlan + list[SectionAgentDraft]",
        output_schema="FinalDocument",
        prompt_policy="Format and assemble only; do not rewrite body content.",
        allowed_actions=["assemble markdown", "add metadata"],
        forbidden_actions=["change facts", "invent citations"],
    )
)


class FormatterAgent(BaseWritingAgent):
    """Assemble final markdown."""

    spec = FORMATTER_SPEC

    def _run(
        self,
        request: WritingRequest,
        plan: WritingPlan,
        drafts: list[SectionAgentDraft],
        *,
        metadata: dict[str, object] | None = None,
    ) -> FinalDocument:
        body = "\n\n".join(draft.content.strip() for draft in drafts)
        return FinalDocument(
            title=plan.title,
            markdown=(
                f"# {plan.title}\n\n"
                f"> Document type: {request.document_type.value}; audience: {request.audience}; "
                f"target length: {request.target_length}.\n\n"
                f"{body}\n"
            ),
            metadata=metadata or {},
        )

