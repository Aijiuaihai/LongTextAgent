from writing_agent.config import Settings
from writing_agent.web.services import job_service
from writing_agent.web.services.schemas import JobCreateRequest, ResumeRequest


def test_web_multi_agent_resume_uses_multi_workflow(monkeypatch, tmp_path) -> None:
    settings = Settings(
        output_dir=tmp_path / "outputs",
        checkpoint_db_path=tmp_path / "outputs" / "checkpoints.sqlite",
    )
    created = job_service.create_job(
        JobCreateRequest(topic="web multi resume", mode="multi", review_outline=True),
        settings=settings,
    )
    job = job_service.get_job(created.job_id, settings)
    assert job is not None
    job.status = "interrupted"
    job.interrupt_payload = {"step": "multi_agent_outline_review"}
    job_service.save_job(job, settings)

    called = {"multi": False}

    def fake_resume(thread_id, review, **kwargs):
        called["multi"] = True
        return {
            "thread_id": thread_id,
            "current_step": "multi_agent_export",
            "output_path": str(tmp_path / "outputs" / "out.md"),
            "output_paths": {"markdown": str(tmp_path / "outputs" / "out.md")},
            "agent_results": [{"agent_name": "formatter", "status": "success"}],
            "supervisor_decisions": [],
            "evaluation_result": {"ok": True},
        }

    monkeypatch.setattr(job_service, "resume_multi_agent_workflow", fake_resume)

    resumed = job_service.resume_job(
        created.job_id,
        ResumeRequest(review="approved"),
        settings=settings,
    )

    assert called["multi"] is True
    assert resumed.status == "completed"
    assert resumed.current_step == "multi_agent_export"
    assert resumed.agent_results
