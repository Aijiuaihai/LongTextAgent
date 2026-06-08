import os

import pytest

from writing_agent.config import Settings
from writing_agent.graph.workflow import run_writing_workflow
from writing_agent.models import WritingRequest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def test_end_to_end_generation_uses_temp_outputs(tmp_path) -> None:
    if os.getenv("RUN_INTEGRATION_TESTS", "").lower() != "true":
        pytest.skip("Set RUN_INTEGRATION_TESTS=true.")

    settings = Settings(
        output_dir=tmp_path / "outputs",
        checkpoint_db_path=tmp_path / "outputs" / "checkpoints.sqlite",
    )
    result = run_writing_workflow(
        {
            "request": WritingRequest(topic="Integration report"),
            "output_dir": str(tmp_path / "outputs"),
            "output_format": "markdown",
            "use_llm": False,
        },
        settings=settings,
        thread_id="integration-e2e",
    )

    assert result["output_path"].endswith(".md")
