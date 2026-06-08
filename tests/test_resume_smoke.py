from pathlib import Path

from writing_agent.config import Settings
from writing_agent.graph.workflow import resume_writing_workflow, run_writing_workflow
from writing_agent.models import WritingRequest


def test_resume_from_outline_review_exports_document(tmp_path) -> None:
    settings = Settings(
        output_dir=tmp_path / "outputs",
        checkpoint_db_path=tmp_path / "outputs" / "checkpoints.sqlite",
    )
    request = WritingRequest(topic="Resume smoke")

    paused = run_writing_workflow(
        {
            "request": request,
            "pause_after_outline": True,
        },
        settings=settings,
        thread_id="resume-smoke",
        use_llm=False,
    )

    assert paused["thread_id"] == "resume-smoke"
    assert paused["current_step"] == "plan_outline"
    assert paused["awaiting_human_review"] is True
    assert "__interrupt__" in paused

    resumed = resume_writing_workflow(
        "resume-smoke",
        "Outline approved. Please continue.",
        settings=settings,
    )

    output_path = Path(resumed["output_path"])
    assert resumed["current_step"] == "export_document"
    assert output_path.exists()
    assert "Resume smoke" in output_path.read_text(encoding="utf-8")
