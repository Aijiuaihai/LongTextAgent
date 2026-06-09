"""WriterAgent."""

from writing_agent.agents.base import AgentSpec, BaseWritingAgent, register_agent
from writing_agent.agents.protocols import SectionAgentDraft, SectionWritingTask

WRITER_SPEC = register_agent(
    AgentSpec(
        name="writer",
        responsibility="Write section drafts from a section task and evidence pack.",
        input_schema="SectionWritingTask",
        output_schema="SectionAgentDraft",
        prompt_policy="Use only retrieved evidence; preserve citation policy.",
        allowed_actions=[
            "write section prose",
            "cite supplied chunks",
            "mark insufficient evidence",
        ],
        forbidden_actions=["invent source_path", "invent chunk_id", "change section goal"],
    )
)


class WriterAgent(BaseWritingAgent):
    """Write one section with citation discipline."""

    spec = WRITER_SPEC

    def _run(self, task: SectionWritingTask) -> SectionAgentDraft:
        section = task.section_plan
        evidence = task.evidence_pack.results
        if not evidence:
            references = "* 本节资料依据不足：缺少可验证的检索资料。"
            insufficient = True
            citations: list[str] = []
            used: list[str] = []
        else:
            citations = [f"{item.source_path}#{item.chunk_id}" for item in evidence]
            used = citations
            references = "\n".join(
                f"* [source: {item.source_path}#{item.chunk_id}] "
                f"支持本节关于{section.title}的论述。"
                for item in evidence
            )
            insufficient = False
        content = (
            f"## {section.title}\n\n"
            f"{section.goal}\n\n"
            f"本节围绕 {', '.join(section.key_points) or section.title} 展开，"
            "并保留可追踪依据。若资料不足，明确标注依据缺口。\n\n"
            f"### 参考依据\n\n{references}\n"
        )
        return SectionAgentDraft(
            title=section.title,
            content=content,
            citations=citations,
            evidence_used=used,
            insufficient_evidence=insufficient,
        )
