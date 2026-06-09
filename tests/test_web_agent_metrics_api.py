from fastapi.testclient import TestClient

from writing_agent.config import Settings
from writing_agent.web import app as web_app
from writing_agent.web.app import create_app
from writing_agent.web.services import job_service


def test_web_agent_metrics_api(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(web_app.jobs, "run_job", lambda *args, **kwargs: None)
    settings = Settings(output_dir=tmp_path / "outputs", data_dir=tmp_path / "data")
    client = TestClient(create_app(settings))

    created = client.post("/api/jobs", json={"topic": "Metrics", "mode": "multi"}).json()
    job = job_service.get_job(created["job_id"], settings)
    assert job is not None
    job.agent_metrics = {
        "thread_id": job.thread_id,
        "mode": "multi",
        "total_agents_run": 4,
        "researcher": {"retrieved_chunks": 5},
    }
    job_service.save_job(job, settings)

    metrics = client.get(f"/api/jobs/{created['job_id']}/agent-metrics").json()

    assert metrics["total_agents_run"] == 4
    assert metrics["researcher"]["retrieved_chunks"] == 5
