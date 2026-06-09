from fastapi.testclient import TestClient

from writing_agent.config import Settings
from writing_agent.web.app import create_app
from writing_agent.web.services.event_service import append_event


def test_web_sse_events_stream_existing_events(tmp_path) -> None:
    settings = Settings(output_dir=tmp_path / "outputs", data_dir=tmp_path / "data")
    append_event("job-1", "completed", message="done", settings=settings)
    client = TestClient(create_app(settings))

    with client.stream("GET", "/api/jobs/job-1/events") as response:
        body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert "event: completed" in body
