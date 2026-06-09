from fastapi.testclient import TestClient

from writing_agent.config import Settings
from writing_agent.web import app as web_app
from writing_agent.web.app import create_app


def test_web_job_api_accepts_multi_agent_mode(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(web_app.jobs, "run_job", lambda *args, **kwargs: None)
    settings = Settings(output_dir=tmp_path / "outputs", data_dir=tmp_path / "data")
    client = TestClient(create_app(settings))

    created = client.post(
        "/api/jobs",
        json={
            "topic": "Multi Web",
            "mode": "multi",
            "max_agent_rounds": 2,
            "agent_debug": True,
        },
    ).json()
    detail = client.get(f"/api/jobs/{created['job_id']}").json()

    assert detail["request"]["mode"] == "multi"
    assert detail["request"]["max_agent_rounds"] == 2
