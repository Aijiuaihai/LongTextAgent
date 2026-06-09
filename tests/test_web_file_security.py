import pytest

from writing_agent.config import Settings
from writing_agent.web.security import ensure_deletable_upload, sanitize_filename


def test_upload_filename_is_sanitized() -> None:
    assert sanitize_filename("../需求 文档.md").endswith(".md")
    with pytest.raises(ValueError):
        sanitize_filename("malware.exe")


def test_delete_is_limited_to_uploads(tmp_path) -> None:
    settings = Settings(output_dir=tmp_path / "outputs", data_dir=tmp_path / "data")
    outside = tmp_path / "data" / "source.md"
    outside.parent.mkdir(parents=True)
    outside.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError):
        ensure_deletable_upload(outside, settings)

