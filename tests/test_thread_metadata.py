from pathlib import Path

from writing_agent.checkpoints import (
    inspect_thread,
    list_threads,
    metadata_path,
    update_thread_metadata,
)
from writing_agent.config import Settings


def test_thread_metadata_round_trip(tmp_path) -> None:
    settings = Settings(output_dir=tmp_path / "outputs")

    update_thread_metadata(
        "thread-1",
        {
            "request": {"topic": "Metadata test"},
            "current_step": "plan_outline",
            "section_drafts": [],
            "review_findings": [],
        },
        interrupted=True,
        settings=settings,
    )

    assert metadata_path(settings) == Path(tmp_path / "outputs" / "thread_metadata.json")
    threads = list_threads(settings)
    assert threads[0]["thread_id"] == "thread-1"

    summary = inspect_thread("thread-1", settings)
    assert summary is not None
    assert summary["request_topic"] == "Metadata test"
    assert summary["interrupted"] is True
    assert summary["current_step"] == "plan_outline"
