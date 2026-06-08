import sys
from pathlib import Path

from writing_agent.cli import build_doctor_report


def test_doctor_report_is_secret_safe(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")
    Path("outputs").mkdir()

    report = build_doctor_report()

    assert report["python_version"] == ".".join(str(part) for part in sys.version_info[:3])
    assert report["python_requires"] == ">=3.11"
    assert report["cwd"] == str(tmp_path)
    assert "secret-value" not in str(report)
    assert "checkpoint_db_path" in report
