"""Local document loader placeholder."""


def load_sources(paths: list[str]) -> list[dict[str, str]]:
    """Load source documents from paths."""

    return [{"path": path, "title": path, "content_preview": "", "full_text": ""} for path in paths]

