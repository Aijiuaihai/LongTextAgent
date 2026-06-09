from writing_agent.config import Settings
from writing_agent.graph.multi_agent_workflow import run_multi_agent_workflow
from writing_agent.models import WritingRequest


def test_multi_agent_interrupts_for_final_review(tmp_path) -> None:
    settings = Settings(
        output_dir=tmp_path / "outputs",
        checkpoint_db_path=tmp_path / "outputs" / "checkpoints.sqlite",
    )

    paused = run_multi_agent_workflow(
        {
            "request": WritingRequest(topic="Final Review Demo"),
            "review_final": True,
            "rag_enabled": False,
        },
        settings=settings,
        thread_id="multi-final-review",
        max_rounds=1,
    )

    assert paused["awaiting_human_review"] is True
    assert paused["current_step"] == "multi_agent_final_review"
    assert "__interrupt__" in paused
    assert paused["final_document"]
