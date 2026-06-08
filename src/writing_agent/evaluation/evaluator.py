"""Evaluation entrypoints."""

from pathlib import Path
from typing import Any

from writing_agent.evaluation.metrics import evaluate_text


def evaluate_markdown(path: Path | str) -> dict[str, Any]:
    """Evaluate a markdown file."""

    resolved = Path(path)
    markdown = resolved.read_text(encoding="utf-8")
    result = evaluate_text(markdown)
    result["file"] = str(resolved)
    return result

