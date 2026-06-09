"""PlannerAgent."""

from writing_agent.agents.base import AgentSpec, BaseWritingAgent, register_agent
from writing_agent.models import SectionPlan, SourceNote, WritingPlan, WritingRequest

PLANNER_SPEC = register_agent(
    AgentSpec(
        name="planner",
        responsibility="Generate a structured outline and section tasks.",
        input_schema="WritingRequest + list[SourceNote]",
        output_schema="WritingPlan",
        prompt_policy="Plan sections and evidence needs; do not write full prose.",
        allowed_actions=["create outline", "split sections", "identify evidence needs"],
        forbidden_actions=["write complete body", "invent evidence"],
    )
)


class PlannerAgent(BaseWritingAgent):
    """Create an executable writing plan."""

    spec = PLANNER_SPEC

    def _run(self, request: WritingRequest, source_notes: list[SourceNote]) -> WritingPlan:
        evidence = "Use retrieved sources" if source_notes else "Mark evidence gaps"
        return WritingPlan(
            title=request.topic,
            abstract_goal=(
                f"Create a {request.document_type.value} for {request.audience}, "
                f"target length {request.target_length}, style: {request.style}."
            ),
            sections=[
                SectionPlan(
                    title="Background and Objectives",
                    goal="Clarify context, objectives, scope, and success criteria.",
                    key_points=["context", "objectives", "scope"],
                    evidence_needed=[evidence],
                    estimated_words=700,
                ),
                SectionPlan(
                    title="Technical Approach",
                    goal="Explain architecture, workflow, resources, and milestones.",
                    key_points=["architecture", "workflow", "milestones"],
                    evidence_needed=[evidence],
                    estimated_words=1200,
                ),
                SectionPlan(
                    title="Risk Control and Acceptance",
                    goal="Describe risks, mitigations, acceptance metrics, and next steps.",
                    key_points=["risks", "controls", "acceptance"],
                    evidence_needed=[evidence],
                    estimated_words=900,
                ),
            ],
            risks=["Evidence coverage must be verified before delivery."],
        )

