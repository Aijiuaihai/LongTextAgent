"""Batch report models and persistence."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    """Return current UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON with parent directory creation."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_failed_tasks(path: Path, tasks: list[dict[str, Any]]) -> None:
    """Write failed task JSONL."""

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(task, ensure_ascii=False) for task in tasks]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
