from pathlib import Path

from writing_agent.config import Settings
from writing_agent.graph.multi_agent_workflow import (
    resume_multi_agent_workflow,
    run_multi_agent_workflow,
)
from writing_agent.models import WritingRequest


def test_multi_agent_resume_from_outline_review_exports_document(tmp_path) -> None:
    settings = Settings(
        output_dir=tmp_path / "outputs",
        checkpoint_db_path=tmp_path / "outputs" / "checkpoints.sqlite",
    )
    thread_id = "multi-resume-outline"

    paused = run_multi_agent_workflow(
        {
            "request": WritingRequest(topic="Multi resume demo"),
            "output_dir": str(tmp_path / "outputs"),
            "review_outline": True,
            "rag_enabled": False,
        },
        settings=settings,
        thread_id=thread_id,
        max_rounds=1,
    )

    assert paused["awaiting_human_review"] is True

    resumed = resume_multi_agent_workflow(
        thread_id,
        {"action": "approve", "notes": "Outline approved."},
        settings=settings,
    )

    output_path = Path(resumed["output_path"])
    assert output_path.exists()
    assert resumed["current_step"] == "multi_agent_export"
    assert "Multi resume demo" in output_path.read_text(encoding="utf-8")
