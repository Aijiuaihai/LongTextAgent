from writing_agent.agents.protocols import AgentMessage, EvidencePack, MultiAgentState
from writing_agent.models import WritingRequest


def test_agent_protocols_are_serializable() -> None:
    state = MultiAgentState(
        request=WritingRequest(topic="Demo"),
        evidence_packs=[EvidencePack(section_title="A", query="q")],
        agent_messages=[AgentMessage(role="agent", agent_name="planner", content="ok")],
    )

    payload = state.model_dump(mode="json")

    assert payload["request"]["topic"] == "Demo"
    assert payload["evidence_packs"][0]["insufficient_evidence"] is False

