"""LangGraph workflow builder placeholder."""

from writing_agent.graph.state import WritingState


def build_workflow() -> object:
    """Build the writing workflow graph."""

    raise NotImplementedError("Writing workflow is not implemented yet.")


def run_writing_workflow(initial_state: WritingState) -> WritingState:
    """Run the writing workflow."""

    return initial_state

