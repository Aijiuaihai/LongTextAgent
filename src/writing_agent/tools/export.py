"""Document export placeholder."""

from pathlib import Path


def export_markdown(
    markdown: str,
    output_dir: Path | str = "./outputs",
    title: str = "document",
) -> Path:
    """Export markdown content to a deterministic placeholder file."""

    output_path = Path(output_dir) / f"{title}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path
