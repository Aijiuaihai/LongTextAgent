from fastapi.testclient import TestClient

from writing_agent.config import Settings
from writing_agent.web import app as web_app
from writing_agent.web.app import create_app
from writing_agent.web.services import job_service


def test_web_multi_agent_resume_endpoint(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(web_app.jobs, "run_job", lambda *args, **kwargs: None)
    settings = Settings(output_dir=tmp_path / "outputs", data_dir=tmp_path / "data")
    client = TestClient(create_app(settings))

    created = client.post(
        "/api/jobs",
        json={"topic": "Web Multi Resume", "mode": "multi", "review_outline": True},
    ).json()
    job = job_service.get_job(created["job_id"], settings)
    assert job is not None
    job.status = "interrupted"
    job.current_step = "multi_agent_outline_review"
    job.interrupt_payload = {"step": "multi_agent_outline_review"}
    job_service.save_job(job, settings)

    def fake_resume_multi_agent_workflow(*args, **kwargs):
        return {
            "current_step": "multi_agent_export",
            "output_path": str(tmp_path / "outputs" / "demo.md"),
            "output_paths": {"markdown": str(tmp_path / "outputs" / "demo.md")},
            "agent_results": [{"agent_name": "planner", "status": "success"}],
            "supervisor_decisions": [],
            "evaluation_result": {"rule_score": 1},
        }

    monkeypatch.setattr(
        job_service,
        "resume_multi_agent_workflow",
        fake_resume_multi_agent_workflow,
    )

    resumed = client.post(
        f"/api/jobs/{created['job_id']}/resume",
        json={"review": "Outline approved."},
    ).json()

    assert resumed["status"] == "completed"
    assert resumed["current_step"] == "multi_agent_export"
    assert resumed["agent_results"][0]["agent_name"] == "planner"
