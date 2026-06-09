from pydantic import BaseModel

from writing_agent.agents.retry import run_with_structured_retry


class RetryOutput(BaseModel):
    ok: bool
    message: str


def test_structured_retry_repairs_invalid_json() -> None:
    calls = {"count": 0}

    def fake_llm(prompt=None):
        calls["count"] += 1
        if calls["count"] == 1:
            return "not json"
        assert prompt and "Return only a valid JSON object" in prompt
        return '{"ok": true, "message": "fixed"}'

    result = run_with_structured_retry("demo", fake_llm, RetryOutput, max_retries=2)

    assert result.status == "success"
    assert result.output["value"]["ok"] is True
    assert result.errors
    assert result.warnings
