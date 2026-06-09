from writing_agent.config import Settings
from writing_agent.web.services.job_service import create_job, get_job
from writing_agent.web.services.schemas import JobCreateRequest


def test_web_job_service_persists_job_metadata(tmp_path) -> None:
    settings = Settings(output_dir=tmp_path / "outputs", data_dir=tmp_path / "data")

    created = create_job(JobCreateRequest(topic="Demo"), settings=settings)
    saved = get_job(created.job_id, settings)

    assert saved is not None
    assert saved.topic == "Demo"
    assert saved.thread_id == created.thread_id
    assert saved.events

