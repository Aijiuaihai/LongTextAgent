from writing_agent.graph.workflow import run_writing_workflow


def test_workflow_placeholder_returns_initial_state() -> None:
    state = {"current_step": "start", "errors": []}

    result = run_writing_workflow(state)

    assert result == state

