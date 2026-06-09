from pydantic import BaseModel

from writing_agent.agents.retry import run_with_structured_retry


class DefaultOutput(BaseModel):
    status: str = "fallback"


def test_structured_retry_uses_default_fallback_when_available() -> None:
    result = run_with_structured_retry(
        "fallback-demo",
        lambda prompt=None: "still not json",
        DefaultOutput,
        max_retries=1,
    )

    assert result.status == "success"
    assert result.output["value"]["status"] == "fallback"
    assert "fallback output used" in result.warnings[-1]
