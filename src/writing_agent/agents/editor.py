"""EditorAgent."""

from writing_agent.agents.base import AgentSpec, BaseWritingAgent, register_agent
from writing_agent.agents.protocols import SectionAgentDraft
from writing_agent.models import ReviewFinding

EDITOR_SPEC = register_agent(
    AgentSpec(
        name="editor",
        responsibility="Apply targeted revisions from review findings.",
        input_schema="list[SectionAgentDraft] + list[ReviewFinding]",
        output_schema="list[SectionAgentDraft]",
        prompt_policy="Do not change facts or fabricate citations.",
        allowed_actions=[
            "tighten transitions",
            "mark unresolved issues",
            "preserve legal citations",
        ],
        forbidden_actions=["invent evidence", "rewrite outside findings"],
    )
)


class EditorAgent(BaseWritingAgent):
    """Apply conservative edits."""

    spec = EDITOR_SPEC

    def _run(
        self,
        drafts: list[SectionAgentDraft],
        findings: list[ReviewFinding],
    ) -> list[SectionAgentDraft]:
        if not findings:
            return drafts
        notes = "\n".join(f"- {finding.suggestion}" for finding in findings)
        edited = []
        for draft in drafts:
            edited.append(
                draft.model_copy(
                    update={"content": f"{draft.content}\n\n### 修订说明\n\n{notes}\n"}
                )
            )
        return edited
