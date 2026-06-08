from writing_agent.cli import build_trace_check_report
from writing_agent.config import get_settings


def test_trace_check_report_does_not_expose_key(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "secret")
    get_settings.cache_clear()

    report = build_trace_check_report()

    assert report["api_key_detected"] is True
    assert "secret" not in str(report)
    get_settings.cache_clear()
