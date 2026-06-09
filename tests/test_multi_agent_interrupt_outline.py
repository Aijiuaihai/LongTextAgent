from writing_agent.config import Settings
from writing_agent.graph.multi_agent_workflow import run_multi_agent_workflow
from writing_agent.models import WritingRequest


def _interrupt_value(result):
    payload = result["__interrupt__"]
    if isinstance(payload, list):
        first = payload[0]
        return getattr(first, "value", first)
    return getattr(payload, "value", payload)


def test_multi_agent_interrupts_for_outline_review(tmp_path) -> None:
    settings = Settings(
        output_dir=tmp_path / "outputs",
        checkpoint_db_path=tmp_path / "outputs" / "checkpoints.sqlite",
    )

    result = run_multi_agent_workflow(
        {
            "request": WritingRequest(topic="Outline review demo"),
            "output_dir": str(tmp_path / "outputs"),
            "review_outline": True,
            "rag_enabled": False,
        },
        settings=settings,
        thread_id="multi-outline-review",
        max_rounds=1,
    )

    payload = _interrupt_value(result)
    assert result["awaiting_human_review"] is True
    assert payload["step"] == "multi_agent_outline_review"
    assert payload["mode"] == "multi"
    assert "current_outline" in payload
    assert "add_section" in payload["allowed_actions"]
