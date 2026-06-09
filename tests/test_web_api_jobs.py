from fastapi.testclient import TestClient

from writing_agent.config import Settings
from writing_agent.web import app as web_app
from writing_agent.web.app import create_app


def test_jobs_api_create_list_detail_and_cancel(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(web_app.jobs, "run_job", lambda *args, **kwargs: None)
    client = TestClient(
        create_app(Settings(output_dir=tmp_path / "outputs", data_dir=tmp_path / "data"))
    )

    created = client.post("/api/jobs", json={"topic": "Web API Job"}).json()
    job_id = created["job_id"]

    assert created["status"] == "pending"
    assert client.get("/api/jobs").json()[0]["job_id"] == job_id
    assert client.get(f"/api/jobs/{job_id}").json()["topic"] == "Web API Job"
    assert client.post(f"/api/jobs/{job_id}/cancel").json()["status"] == "cancel_requested"

