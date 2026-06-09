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

    paused = run_multi_agent_workflow(
        {
            "request": WritingRequest(topic="Multi Resume Demo"),
            "review_outline": True,
            "rag_enabled": False,
        },
        settings=settings,
        thread_id="multi-resume",
        max_rounds=1,
    )

    assert paused["current_step"] == "multi_agent_outline_review"

    resumed = resume_multi_agent_workflow(
        "multi-resume",
        {"action": "approve", "notes": "Continue."},
        settings=settings,
    )

    output_path = Path(resumed["output_path"])
    assert resumed["current_step"] == "multi_agent_export"
    assert output_path.exists()
    assert "Multi Resume Demo" in output_path.read_text(encoding="utf-8")
