from writing_agent.agents.planner import PlannerAgent
from writing_agent.models import WritingRequest


def test_planner_agent_creates_structured_plan() -> None:
    plan = PlannerAgent()._run(WritingRequest(topic="Demo plan"), [])

    assert plan.title == "Demo plan"
    assert len(plan.sections) >= 3

