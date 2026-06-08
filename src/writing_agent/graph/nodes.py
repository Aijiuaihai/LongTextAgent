"""Workflow node placeholders."""

from writing_agent.graph.state import WritingState


def parse_request_node(state: WritingState) -> WritingState:
    """Placeholder request parser node."""

    return {**state, "current_step": "parse_request"}

